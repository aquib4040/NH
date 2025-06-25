import aiohttp
import asyncio
from bs4 import BeautifulSoup

from pyrogram import Client, filters
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
)

from config import APP_ID as API_ID, API_HASH, BOT_TOKEN
from database import db  # Import your MongoDB handler

app = Client("inline_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


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

        # Save bot header/footer config for user
        await db.set_bot(user_id, client.me.username)
        await db.set_header(user_id, f"🔍 You searched: {query}")

        # Example of making footer dynamic: showing current page number
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


print("Bot started!")
app.run()
