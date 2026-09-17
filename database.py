from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime

client = MongoClient(MONGO_URI)
db = client["challenge_bot"]

users = db["users"]
challenges = db["challenges"]
participants = db["participants"]

def register_user_start(user_id, username):
    if not users.find_one({"user_id": user_id}):
        users.insert_one({
            "user_id": user_id,
            "username": username,
            "started_at": datetime.utcnow()
        })

def get_total_starts():
    return users.count_documents({})

def create_challenge(owner_id, channel_id, channel_link, data):
    challenge = {
        "owner_id": owner_id,
        "channel_id": channel_id,
        "channel_link": channel_link,
        "winners_count": data["winners_count"],
        "prizes": data["prizes"],
        "start_time": data["start_time"],
        "end_time": data["end_time"],
        "stars_enabled": data.get("stars_enabled", False),
        "stars_rate": data.get("stars_rate", 0),
        "created_at": datetime.utcnow(),
        "active": True,
        "reminded": False
    }
    result = challenges.insert_one(challenge)
    return str(result.inserted_id)

def add_participant(challenge_id, user_id, name, age, city, photo_file_id, channel_id):
    count = participants.count_documents({"challenge_id": challenge_id})
    participant = {
        "challenge_id": challenge_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "number": count + 1,
        "name": name,
        "age": age,
        "city": city,
        "photo_file_id": photo_file_id,
        "likes": 0,
        "stars_received": 0,
        "liked_by": []
    }
    participants.insert_one(participant)
    return count + 1

def add_like(participant_id, liker_user_id):
    p = participants.find_one({"_id": participant_id})
    if liker_user_id in p.get("liked_by", []):
        return False
    participants.update_one(
        {"_id": participant_id},
        {"$inc": {"likes": 1}, "$push": {"liked_by": liker_user_id}}
    )
    return True

def remove_like_on_leave(channel_id, left_user_id):
    affected = participants.find({"channel_id": channel_id, "liked_by": left_user_id})
    for p in affected:
        participants.update_one(
            {"_id": p["_id"]},
            {"$inc": {"likes": -1}, "$pull": {"liked_by": left_user_id}}
        )

def get_leaderboard(challenge_id, stars_rate=0):
    docs = list(participants.find({"challenge_id": challenge_id}))
    for d in docs:
        d["total_score"] = d.get("likes", 0) + d.get("stars_received", 0) * stars_rate
    docs.sort(key=lambda x: x["total_score"], reverse=True)
    return docs
