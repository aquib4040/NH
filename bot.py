import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import requests
from bs4 import BeautifulSoup
from config import API_HASH, TG_BOT_TOKEN, OWNER_ID, APP_ID as API_ID
from database import db

bot = Client("hmanga_bot", api_id=API_ID, api_hash=API_HASH, bot_token=TG_BOT_TOKEN)

# --- Helper Functions --- #
def nhentai_search(query):
    url = f"https://nhentai.net/search/?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    results = []
    for gallery in soup.select(".gallery")[:5]:
        code = gallery['href'].split("/")[2]
        title = gallery.select_one(".caption").text.strip()
        thumb = gallery.select_one("img")['data-src'].replace("t.nhentai.net", "i.nhentai.net").replace("/t.jpg", "/cover.jpg")
        results.append((code, title, thumb))
    return results

def generate_nhentai_buttons(results):
    buttons = []
    for code, title, _ in results:
        buttons.append([
            InlineKeyboardButton("📥 Read Online", url=f"https://nhentai.net/g/{code}"),
            InlineKeyboardButton("📄 Download PDF", url=f"https://api.hentaidownloader.org/nhentai/pdf/{code}")
        ])
    return buttons

# --- Command Handlers --- #
@bot.on_message(filters.command("start") & filters.private)
async def start_handler(_, message):
    await message.reply(
        "👋 Welcome to H-Manga Bot!\nSend a manga name and choose your source to search.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Support", url="https://t.me/yourchannel")],
            [InlineKeyboardButton("🔍 Search Examples", callback_data="help_examples")]
        ])
    )

@bot.on_message(filters.private & filters.text)
async def search_handler(client, message):
    query = message.text.strip()
    if not query:
        return await message.reply("❌ Please enter a valid search term.")

    await db.save_history(user_id=message.from_user.id, query=query)

    buttons = [
        [
            InlineKeyboardButton("🔴 NHentai", callback_data=f"src_nh_{query}"),
            InlineKeyboardButton("🟠 HBrowse", callback_data=f"src_hb_{query}"),
            InlineKeyboardButton("🔵 8Muses", callback_data=f"src_8m_{query}")
        ]
    ]
    await message.reply(
        f"🔍 You searched: <b>{query}</b>\nPlease select a site to fetch results from:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="html"
    )

@bot.on_callback_query()
async def source_callback(client, callback_query):
    data = callback_query.data
    await callback_query.answer()

    if data == "help_examples":
        return await callback_query.message.edit_text("📘 Example Searches:\n- Naruto\n- One Piece\n- Overwatch\n\nType in PM to search.")

    if not data.startswith("src_"):
        return

    _, source, query = data.split("_", 2)

    if source == "nh":
        results = nhentai_search(query)
        if results:
            code, title, thumb = results[0]
            buttons = generate_nhentai_buttons(results)
            caption = f"<b>🔞 {title}</b>\n📖 <i>Code</i>: <code>{code}</code>\n\n🔗 https://nhentai.net/g/{code}"
            await callback_query.message.reply_photo(photo=thumb, caption=caption, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="html")
        else:
            await callback_query.message.edit_text("❌ No results found for NHentai.")

    elif source == "hb":
        link = f"https://www.hbrowse.com/search?query={query}"
        await callback_query.message.edit_text(f"📚 HBrowse results for: <b>{query}</b>\n🔗 {link}", parse_mode="html")

    elif source == "8m":
        link = f"https://comics.8muses.com/search?q={query}"
        await callback_query.message.edit_text(f"📚 8Muses results for: <b>{query}</b>\n🔗 {link}", parse_mode="html")

    else:
        await callback_query.message.edit_text("❌ Unknown source selected.")

# --- Notify Owner on Startup --- #
async def notify_owner():
    try:
        await bot.send_message(OWNER_ID, "✅ Bot restarted and is now online.")
    except Exception as e:
        print(f"Failed to notify owner: {e}")

# --- Main Run --- #
async def main():
    await bot.start()
    await notify_owner()
    print("🤖 Bot is running...")
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
