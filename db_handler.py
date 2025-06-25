import logging
import motor.motor_asyncio
from config import DB_URI, DB_NAME


class MongoHandler:
    def __init__(self, uri, db_name):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.users = self.db.users
        self.history = self.db.history

    async def add_user(self, user_id):
        try:
            await self.users.update_one({"_id": user_id}, {"$setOnInsert": {"joined": True}}, upsert=True)
        except Exception as e:
            logging.error(f"Failed to add user {user_id}: {e}")

    async def get_total_users(self):
        try:
            return await self.users.count_documents({})
        except Exception as e:
            logging.error(f"Error fetching user count: {e}")
            return 0

    async def broadcast_message(self, bot, message):
        total = 0
        async for user in self.users.find({}, {"_id": 1}):
            try:
                await bot.copy_message(chat_id=user["_id"], from_chat_id=message.chat.id, message_id=message.id)
                total += 1
            except Exception as e:
                logging.warning(f"Broadcast to {user['_id']} failed: {e}")
        return total

    async def save_history(self, user_id, query):
        try:
            await self.history.update_one(
                {"_id": user_id},
                {"$push": {"queries": {"$each": [query], "$slice": -10}}},
                upsert=True
            )
        except Exception as e:
            logging.error(f"Error saving history for {user_id}: {e}")

    async def get_history(self, user_id):
        user = await self.history.find_one({"_id": user_id})
        return user.get("queries", []) if user else []

    async def clear_history(self, user_id):
        try:
            result = await self.history.update_one({"_id": user_id}, {"$set": {"queries": []}})
            return result.modified_count
        except Exception as e:
            logging.error(f"Error clearing history for {user_id}: {e}")
            return 0


# Create instance

db = MongoHandler(DB_URI, DB_NAME)
