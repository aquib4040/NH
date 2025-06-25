import aiohttp
import asyncio
import os
from bs4 import BeautifulSoup
from PIL import Image

from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery
)

from config import APP_ID, API_HASH, TG_BOT_TOKEN, START_MSG, START_PIC, OWNER_ID, LOGGER
from database import db  # Import your MongoDB handler

app = Client("inline_bot", api_id=APP_ID, api_hash=API_HASH, bot_token=TG_BOT_TOKEN)


async def search_nhentai(query=None, page=1):
    results = []
    if not query:
        query = "naruto"
    url = f"https://nhentai.net/search/?q={query.replace(' ', '+')}&page={page}"

    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"[ERROR] HTTP {response.status} for query: {query}")
                return []
            html = await response.text()

    soup = BeautifulSoup(html, "html.parser")
    gallery_items = soup.select(".gallery")

    for item in gallery_items[:10]:
        link = item.select_one("a")["href"]
        code = link.split("/")[2]
        title = item.select_one(".caption").text.strip() if item.select_one(".caption") else f"Code {code}"
        thumb = item.select_one("img").get("data-src") or item.select_one("img").get("src")
        if thumb.startswith("//"):
            thumb = "https:" + thumb

        results.append({
            "code": code,
            "title": title,
            "thumb": thumb
        })

    print(f"[DEBUG] Found {len(results)} results for query '{query}'")
    return results


@app.on_inline_query()
async def inline_search(client: Client, inline_query: InlineQuery):
    query = inline_query.query.strip() or "naruto"
    page = int(inline_query.offset) if inline_query.offset else 1
    user_id = inline_query.from_user.id

    try:
        raw_results = await search_nhentai(query, page)
        next_offset = str(page + 1) if len(raw_results) == 10 else ""

        await db.set_bot(user_id, client.me.username)
        await db.set_header(user_id, f"🔍 You searched: {query}")
        footer_text = f"📄 Page {page} • 👨‍💻 @KGN_BOTZ"
        await db.set_footer(user_id, footer_text)

        header = await db.get_header(user_id)
        footer = await db.get_footer(user_id)

        results = []
        for item in raw_results:
            title = item["title"]
            code = item["code"]
            thumb = item["thumb"]

            caption = f"{header}\n\n<b>{title}</b>\n🔗 <a href=\"https://nhentai.net/g/{code}/\">Read Now</a>\n\n<code>Code:</code> {code}\n\n{footer}"

            results.append(
                InlineQueryResultArticle(
                    title=title,
                    description=f"Code: {code}",
                    thumb_url=thumb,
                    input_message_content=InputTextMessageContent(
                        message_text=caption,
                        disable_web_page_preview=False,
                        parse_mode="HTML"
                    ),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📥 Download PDF", callback_data=f"download_{code}")]
                    ])
                )
            )

        await inline_query.answer(results, cache_time=1, is_personal=True, next_offset=next_offset)

    except Exception as e:
        print("[INLINE ERROR]", e)
        await inline_query.answer([], switch_pm_text="⚠️ Search failed", switch_pm_parameter="start")


async def download_page(session, url, filename):
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            raise Exception(f"Failed to download: {url}")
        with open(filename, "wb") as f:
            f.write(await resp.read())


async def download_manga_as_pdf(code, progress_callback=None):
    api_url = f"https://nhentai.net/api/gallery/{code}"
    folder = f"nhentai_{code}"
    os.makedirs(folder, exist_ok=True)

    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception("Gallery not found.")
            data = await resp.json()

        num_pages = len(data["images"]["pages"])
        ext_map = {"j": "jpg", "p": "png", "g": "gif", "w": "webp"}
        media_id = data["media_id"]
        image_paths = []

        for i, page in enumerate(data["images"]["pages"], start=1):
            ext = ext_map.get(page["t"], "jpg")
            url = f"https://i.nhentai.net/galleries/{media_id}/{i}.{ext}"
            path = os.path.join(folder, f"{i:03}.{ext}")
            await download_page(session, url, path)
            image_paths.append(path)
            if progress_callback:
                await progress_callback(i, num_pages, "Downloading")

    pdf_path = f"{folder}.pdf"
    first_img = Image.open(image_paths[0]).convert("RGB")
    first_img.save(pdf_path, format="PDF", save_all=True, append_images=[
        Image.open(p).convert("RGB") for p in image_paths[1:]
    ])

    for img in image_paths:
        os.remove(img)
    os.rmdir(folder)
    return pdf_path


@app.on_callback_query(filters.regex(r"^download_(\d+)$"))
async def handle_download(client: Client, callback: CallbackQuery):
    code = callback.matches[0].group(1)
    pdf_path = None
    msg = None

    try:
        chat_id = callback.message.chat.id if callback.message else callback.from_user.id

        if callback.message:
            msg = await callback.message.reply("📥 Starting download...")
        else:
            await callback.answer("📥 Starting download...")

        async def progress(cur, total, stage):
            percent = int((cur / total) * 100)
            txt = f"{stage}... {percent}%"
            try:
                if msg:
                    await msg.edit(txt)
                else:
                    await callback.edit_message_text(txt)
            except:
                pass

        pdf_path = await download_manga_as_pdf(code, progress)

        if msg:
            await msg.edit("📤 Uploading PDF...")
        else:
            await callback.edit_message_text("📤 Uploading PDF...")

        await client.send_document(chat_id, document=pdf_path, caption=f"📖 Manga: {code}")

    except Exception as e:
        err = f"❌ Error: {e}"
        try:
            if msg:
                await msg.edit(err)
            else:
                await callback.edit_message_text(err)
        except:
            pass
    finally:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)


print("Bot started!")
app.run()
