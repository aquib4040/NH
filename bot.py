import aiohttp
import asyncio
import os
from bs4 import BeautifulSoup
from PIL import Image
from aiohttp import web

from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message
)

from config import APP_ID, API_HASH, TG_BOT_TOKEN, OWNER_ID, LOGGER
from database import db

app = Client("inline_bot", api_id=APP_ID, api_hash=API_HASH, bot_token=TG_BOT_TOKEN)

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_handler(request):
    return web.Response(text="✅ Bot is alive!")

async def web_server():
    web_app = web.Application(client_max_size=100000000)
    web_app.add_routes(routes)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    await site.start()

@app.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 Search Manga", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📤 Deploy on Heroku", url="https://heroku.com/deploy")],
        [InlineKeyboardButton("💻 Contact Developer", url="https://t.me/rohit_1888")]
    ])
    start_pic = os.getenv("START_PIC") or "https://placehold.co/600x400"
    start_msg = os.getenv("START_MESSAGE") or "<b>Hello {mention}, welcome to the bot.</b>"
    try:
        caption = start_msg.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=f"@{message.from_user.username}" if message.from_user.username else None,
            mention=message.from_user.mention,
            id=message.from_user.id
        )
    except Exception:
        caption = f"<b>Hello {message.from_user.mention}, welcome to the bot.</b>"

    try:
        await message.reply_photo(
            photo=start_pic,
            caption=caption,
            reply_markup=keyboard
        )
    except Exception:
        await message.reply_text(
            text=caption,
            reply_markup=keyboard
        )

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def pm_search_handler(client: Client, message: Message):
    query = message.text.strip()
    user_id = message.from_user.id

    try:
        await db.set_bot(user_id, client.me.username)
        await db.set_header(user_id, f"🔍 You searched: {query}")
        footer_text = f"📄 Results • 👨‍💻 @KGN_BOTZ"
        await db.set_footer(user_id, footer_text)

        header = await db.get_header(user_id)
        footer = await db.get_footer(user_id)

        results = await search_nhentai(query)
        if not results:
            await message.reply_text("❌ No results found.")
            return

        for item in results[:5]:
            title = item["title"]
            code = item["code"]
            thumb = item["thumb"]
            caption = f"{header}\n\n<b>{title}</b>\n🔗 <a href=\"https://nhentai.net/g/{code}/\">Read Now</a>\n\n<code>Code:</code> {code}\n\n{footer}"

            try:
                await message.reply_photo(
                    photo=thumb,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📥 PDF", url=f"https://nhentai.to/g/{code}/download/pdf"),
                            InlineKeyboardButton("🌐 Web", url=f"https://nhentai.net/g/{code}/")
                        ]
                    ])
                )
            except:
                await message.reply_text(caption, disable_web_page_preview=True)

    except Exception as e:
        print("[PM SEARCH ERROR]", e)
        await message.reply_text("⚠️ Something went wrong during search.")

async def search_nhentai(query):
    results = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://nhentai.net/search/?q={query}") as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                gallery = soup.find_all("div", class_="gallery")

                for item in gallery:
                    code = item.a['href'].split('/')[2]
                    title = item.find("div", class_="caption").text.strip()
                    thumb = item.img['data-src'] if item.img.has_attr('data-src') else item.img['src']
                    thumb = thumb.replace("t.nhentai.net", "i.nhentai.net").replace("t.jpg", ".jpg")
                    results.append({"code": code, "title": title, "thumb": thumb})
    except Exception as e:
        print("[SEARCH_NHENTAI ERROR]", e)
    return results

async def notify_owner():
    try:
        await app.send_message(OWNER_ID, "🚀 Bot Restarted and Running!")
    except Exception as e:
        print("[NOTIFY_OWNER ERROR]", e)

async def main():
    await app.start()
    print("✅ Bot Started!")
    await notify_owner()
    await web_server()
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
