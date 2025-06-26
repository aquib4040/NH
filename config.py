import os
from os import environ,getenv
import logging
from logging.handlers import RotatingFileHandler

#rohit_1888 on Tg
#--------------------------------------------
#Bot token @Botfather
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "7799059256:AAFol5JZWyL44Ok7jGv5yb5lKkLkXxEUpu0")
API_ID = int(os.environ.get("API_ID", "20697474")) #Your API ID from my.telegram.org
API_HASH = os.environ.get("API_HASH", "1acf41c146d578a57741ab0760208eb4") #Your API Hash from my.telegram.org
#--------------------------------------------

OWNER_ID = int(os.environ.get("OWNER_ID", "5851158054")) # Owner id
#--------------------------------------------
PORT = os.environ.get("PORT", "8080")
#--------------------------------------------
DB_URI = os.environ.get("DATABASE_URL", "mongodb+srv://nar2db1:APMFkvM8w0LUk0R5@cluster0.9xfnq5n.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DATABASE_NAME", "hmanga")

TG_BOT_WORKERS = int(os.environ.get("TG_BOT_WORKERS", "200"))
#--------------------------------------------
START_PIC = os.environ.get("START_PIC", "https://i.ibb.co/BVs6G2mp/5774913404891411876-1.jpg")

#--------------------------------------------
#--------------------------------------------
START_MSG = os.environ.get("START_MESSAGE", "<b>ʜᴇʟʟᴏ {mention}\n\n<blockquote> ɪ ᴀᴍ ʜ-ᴍᴀɴɢᴀ ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ.</blockquote></b>")

#--------------------------------------------
#--------------------------------------------

LOG_FILE_NAME = "postgenbot.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S',
    handlers=[
        RotatingFileHandler(
            LOG_FILE_NAME,
            maxBytes=50000000,
            backupCount=10
        ),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def LOGGER(name: str) -> logging.Logger:
    return logging.getLogger(name)
   
