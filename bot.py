import os
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import TG_BOT_TOKEN, DB_URI, DB_NAME, OWNER_ID, API_ID, API_HASH
from db_handler import db
from sources.nhentai import search_nhentai
from sources.hbrowse import search_hbrowse

logging.basicConfig(level=logging.INFO)

bot = Client(
    name="hmanga-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=TG_BOT_TOKEN
)

@bot.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    await db.add_user(message.from_user.id)
    await message.reply_text(
        f"👋 Hello {message.from_user.mention}!\nWelcome to the H-Manga Bot.\nChoose a source or type your search directly:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Search NHentai", callback_data="choose_src_nhentai"),
                InlineKeyboardButton("🔍 Search HBrowse", callback_data="choose_src_hbrowse")
            ],
            [
                InlineKeyboardButton("📚 History", callback_data="history"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ]
        ])
    )

@bot.on_callback_query(filters.regex("^choose_src_"))
async def callback_choose_source(client, callback_query):
    source = callback_query.data.split("_")[-1]
    await callback_query.message.edit_text(
        f"✅ You selected {source.upper()} as your source. Now send me the manga name.")
    await db.set_user_source(callback_query.from_user.id, source)
    await callback_query.answer()

@bot.on_callback_query(filters.regex("^help"))
async def callback_help(client, callback_query):
    await callback_query.message.edit_text(
        "ℹ️ Just type the name of the H-Manga you want.\nUse the buttons on /start to select a source or view history."
    )
    await callback_query.answer()

@bot.on_callback_query(filters.regex("^history"))
async def callback_history(client, callback_query):
    history = await db.get_history(callback_query.from_user.id)
    if not history:
        await callback_query.message.edit_text("📭 No search history found.")
    else:
        formatted = "\n".join(f"🔹 {item}" for item in history)
        await callback_query.message.edit_text(f"📜 Your recent searches:\n{formatted}")
    await callback_query.answer()

@bot.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply("Please reply to a message to broadcast.")
    total = await db.broadcast_message(client, message.reply_to_message)
    await message.reply(f"✅ Broadcast sent to {total} users.")

@bot.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_handler(client: Client, message: Message):
    count = await db.get_total_users()
    await message.reply(f"📊 Total users: {count}")

@bot.on_message(filters.text & filters.private & ~filters.command(["start", "history", "broadcast", "stats"]))
async def search_handler(client: Client, message: Message):
    query = message.text.strip()
    if not query:
        return

    await db.save_history(message.from_user.id, query)
    user_source = await db.get_user_source(message.from_user.id)

    results = []

    if user_source == "nhentai" or not user_source:
        nhentai_result = await search_nhentai(query)
        if nhentai_result:
            results.append({
                "title": "NHentai",
                "url": nhentai_result['pdf_url'],
                "thumbnail": nhentai_result.get('thumbnail')
            })

    if user_source == "hbrowse" or not user_source:
        hbrowse_result = await search_hbrowse(query)
        if hbrowse_result:
            results.append({
                "title": "HBrowse",
                "url": hbrowse_result['pdf_url'],
                "thumbnail": hbrowse_result.get('thumbnail')
            })

    if not results:
        return await message.reply("❌ No results found on any source.")

    buttons = [
        [InlineKeyboardButton(f"📥 Download from {r['title']}", url=r['url'])] for r in results
    ]

    thumbnail = results[0]['thumbnail'] if results[0].get('thumbnail') else "https://telegra.ph/file/ec17880d61180d3312d6a.jpg"

    await message.reply_photo(
        photo=thumbnail,
        caption=f"🔍 Results for: <b>{query}</b>\nChoose your source below:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def main():
    await bot.start()
    logging.info("✅ Bot Started with worker Procfile")
    try:
        await bot.send_message(OWNER_ID, "🚀 Bot has been deployed and is now running!")
    except Exception as e:
        logging.warning(f"Couldn't send startup message to owner: {e}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
