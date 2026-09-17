from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument
from config import MONGO_URI

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
db = client["challenge_bot"]
users = db["users"]
challenges = db["challenges"]
participants = db["participants"]
reports = db["reports"]
audit_logs = db["audit_logs"]
counters = db["counters"]

for collection, fields in [
    (users, [("user_id", ASCENDING)]),
    (participants, [("challenge_id", ASCENDING), ("user_id", ASCENDING)]),
    (participants, [("challenge_id", ASCENDING), ("number", ASCENDING)]),
]:
    try:
        collection.create_index(fields, unique=True)
    except Exception:
        pass


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def register_user_start(user_id, username=""):
    users.update_one({"user_id": user_id}, {"$set": {"username": username, "last_start_at": now_utc()}, "$setOnInsert": {"started_at": now_utc(), "language": "fa", "blocked": False}}, upsert=True)


def increment_deep_start(challenge_id, user_id):
    challenges.update_one({"_id": challenge_id}, {"$inc": {"deep_link_starts": 1}, "$addToSet": {"deep_link_users": user_id}})


def get_total_starts():
    return users.count_documents({})


def create_challenge(owner_id, owner_username, data):
    doc = dict(data)
    doc.update({"owner_id": owner_id, "owner_username": owner_username, "created_at": now_utc(), "active": True, "reminded": False, "deep_link_starts": 0, "deep_link_users": []})
    result = challenges.insert_one(doc)
    return str(result.inserted_id)


def get_challenge(challenge_id):
    from bson import ObjectId
    try:
        return challenges.find_one({"_id": ObjectId(challenge_id)})
    except Exception:
        return None


def is_blocked(user_id):
    return bool(users.find_one({"user_id": user_id, "blocked": True}))


def add_participant(challenge_id, user_id, name, age, city, photo_file_id, channel_id):
    existing = participants.find_one({"challenge_id": challenge_id, "user_id": user_id})
    if existing:
        return existing["number"], False
    counter_key = f"participant:{challenge_id}"
    counter = counters.find_one_and_update({"_id": counter_key}, {"$inc": {"value": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    number = int(counter["value"])
    doc = {"challenge_id": challenge_id, "channel_id": channel_id, "user_id": user_id, "number": number, "name": name, "age": age, "city": city, "photo_file_id": photo_file_id, "likes": 0, "stars_received": 0, "liked_by": [], "registered_at": now_utc(), "post_message_id": None}
    try:
        participants.insert_one(doc)
    except DuplicateKeyError:
        existing = participants.find_one({"challenge_id": challenge_id, "user_id": user_id})
        return existing["number"], False
    challenges.update_one({"_id": __import__("bson").ObjectId(challenge_id)}, {"$inc": {"registrations": 1}})
    return number, True


def add_like(participant_id, liker_user_id):
    result = participants.update_one({"_id": participant_id, "liked_by": {"$ne": liker_user_id}}, {"$inc": {"likes": 1}, "$push": {"liked_by": liker_user_id}})
    return result.modified_count == 1


def remove_like_on_leave(channel_id, left_user_id):
    for p in participants.find({"channel_id": channel_id, "liked_by": left_user_id}):
        participants.update_one({"_id": p["_id"]}, {"$inc": {"likes": -1}, "$pull": {"liked_by": left_user_id}})


def get_leaderboard(challenge_id, stars_rate=0):
    docs = list(participants.find({"challenge_id": challenge_id}))
    for d in docs:
        d["total_score"] = int(d.get("likes", 0)) + int(d.get("stars_received", 0)) * int(stars_rate or 0)
    docs.sort(key=lambda x: (x["total_score"], x.get("likes", 0), x.get("stars_received", 0)), reverse=True)
    return docs


def create_report(reporter_id, challenge_id, reason, text):
    doc = {"reporter_id": reporter_id, "challenge_id": challenge_id, "reason": reason, "text": text, "created_at": now_utc(), "status": "open"}
    result = reports.insert_one(doc)
    return str(result.inserted_id)


def audit(actor_id, action, challenge_id=None, target_user_id=None, details=""):
    audit_logs.insert_one({"actor_id": actor_id, "action": action, "challenge_id": challenge_id, "target_user_id": target_user_id, "details": details, "created_at": now_utc()})


def owner_challenges(owner_id):
    return list(challenges.find({"owner_id": owner_id}).sort("created_at", -1))
