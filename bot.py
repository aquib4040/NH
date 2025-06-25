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

# Static cookies to simulate a logged-in session on nhentai
COOKIE_JAR = aiohttp.CookieJar()
COOKIE_JAR.update_cookies({
    "cf_clearance": "2968378f2272707dac237fc5e1f12aaf",
    "csrftoken": "sGLJMZAnfdAXdoFR1vAaAsuKI9eYeBHe",
    "sessionid": "93lec8xbayt4zi82gykp11ibde30ovl4"
})

LOGIN_SESSION = None

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

@app.on_callback_query(filters.regex("^getpdf_"))
async def get_pdf(client: Client, callback_query: CallbackQuery):
    code = callback_query.data.split("_", 1)[1]
    pdf_url = f"https://nhentai.net/g/{code}/download/pdf"

    await callback_query.answer("📥 Downloading PDF, please wait...")
    try:
        async with LOGIN_SESSION.get(pdf_url) as resp:
            if resp.status == 200:
                file_bytes = await resp.read()
                await client.send_document(
                    chat_id=callback_query.from_user.id,
                    document=file_bytes,
                    file_name=f"nhentai_{code}.pdf",
                    caption=f"📄 PDF of {code}"
                )
            else:
                await callback_query.message.reply_text("❌ PDF not found or access denied.")
    except Exception as e:
        await callback_query.message.reply_text("❌ Error downloading PDF.")
        print("[PDF DOWNLOAD ERROR]", e)

@app.on_message(filters.private & filters.text & ~filters.command("start"))
async def pm_search_handler(client: Client, message: Message):
    query = message.text.strip()
    user_id = message.from_user.id

    try:
        await db.set_bot(user_id, client.me.username)
        await db.set_header(user_id, f"🔍 You searched: {query}")
        footer_text = f"📄 Results • 👨‍💻 @{client.me.username}"
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

            caption = f"<b>🔥 {title}</b>\n\n{header}\n🆔 <b>Code:</b> <code>{code}</code>\n📖 <a href=\"https://nhentai.net/g/{code}/\">Read Online</a>\n\n{footer}"

            try:
                await message.reply_photo(
                    photo=thumb,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📥 Download PDF", callback_data=f"getpdf_{code}"),
                            InlineKeyboardButton("🌐 View Online", url=f"https://nhentai.net/g/{code}/")
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

async def renew_cookies():
    global LOGIN_SESSION
    while True:
        await asyncio.sleep(3600)  # Renew every hour
        try:
            COOKIE_JAR.clear()
            COOKIE_JAR.update_cookies({
                "cf_clearance": "2968378f2272707dac237fc5e1f12aaf",
                "csrftoken": "sGLJMZAnfdAXdoFR1vAaAsuKI9eYeBHe",
                "sessionid": "93lec8xbayt4zi82gykp11ibde30ovl4"
            })
            if LOGIN_SESSION:
                await LOGIN_SESSION.close()
            LOGIN_SESSION = aiohttp.ClientSession(cookie_jar=COOKIE_JAR)
            print("🔄 Cookies renewed!")
        except Exception as e:
            print("[COOKIE RENEW ERROR]", e)

async def main():
    global LOGIN_SESSION
    LOGIN_SESSION = aiohttp.ClientSession(cookie_jar=COOKIE_JAR)
    await app.start()
    print("✅ Bot Started!")
    await notify_owner()
    await asyncio.gather(web_server(), renew_cookies(), idle())
    await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
