from pymongo import MongoClient
from config import MONGO_URI

mongo = MongoClient(MONGO_URI)
db = mongo['session_bot']
users_col = db['users']

def save_user(user):
    if not users_col.find_one({"user_id": user.id}):
        users_col.insert_one({
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name
        })

def get_all_users():
    return list(users_col.find())
