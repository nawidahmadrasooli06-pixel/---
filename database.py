from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
from config import MONGO_URI

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
db = client["challenge_bot"]
users = db["users"]
challenges = db["challenges"]
participants = db["participants"]
reports = db["reports"]
audit_logs = db["audit_logs"]
blocked_owners = db["blocked_owners"]
challenge_counters = db["challenge_counters"]

users.create_index([("user_id", ASCENDING)], unique=True)
participants.create_index([("challenge_id", ASCENDING), ("user_id", ASCENDING)], unique=True)
participants.create_index([("challenge_id", ASCENDING), ("number", ASCENDING)], unique=True)
participants.create_index([("challenge_id", ASCENDING)])
challenges.create_index([("owner_id", ASCENDING), ("created_at", DESCENDING)])
challenges.create_index([("active", ASCENDING), ("end_time", ASCENDING)])
reports.create_index([("challenge_id", ASCENDING), ("created_at", DESCENDING)])


def now_utc():
    return datetime.now(timezone.utc)


def register_user_start(user_id, username="", language=None):
    users.update_one(
        {"user_id": user_id},
        {"$set": {"username": username or ""}, "$setOnInsert": {"user_id": user_id, "started_at": now_utc(), "language": language or "fa", "blocked": False}, "$inc": {"start_count": 1}},
        upsert=True,
    )


def set_user_language(user_id, language):
    users.update_one({"user_id": user_id}, {"$set": {"language": language}}, upsert=True)


def get_total_starts():
    return users.count_documents({})


def is_blocked(user_id):
    return bool(blocked_owners.find_one({"owner_id": user_id, "blocked": True}) or users.find_one({"user_id": user_id, "blocked": True}))


def set_blocked(user_id, blocked=True):
    blocked_owners.update_one({"owner_id": user_id}, {"$set": {"owner_id": user_id, "blocked": blocked}}, upsert=True)
    users.update_one({"user_id": user_id}, {"$set": {"blocked": blocked}}, upsert=True)


def audit(actor_id, action, challenge_id=None, target_user_id=None, details=""):
    audit_logs.insert_one({"actor_id": actor_id, "action": action, "challenge_id": challenge_id, "target_user_id": target_user_id, "details": details, "created_at": now_utc()})


def create_challenge(owner_id, owner_username, data):
    doc = {
        "owner_id": owner_id,
        "owner_username": owner_username or "",
        "title": data["title"],
        "channel_id": data["channel_id"],
        "channel_username": data.get("channel_username", ""),
        "channel_link": data.get("channel_link", ""),
        "timezone": data["timezone"],
        "start_time": data["start_time"],
        "end_time": data["end_time"],
        "duration_hours": data["duration_hours"],
        "winners_count": data["winners_count"],
        "prizes": data["prizes"],
        "rules": data.get("rules", ""),
        "stars_enabled": data.get("stars_enabled", False),
        "stars_rate": data.get("stars_rate", 0),
        "created_at": now_utc(),
        "active": True,
        "reminded": False,
        "ended_at": None,
        "deep_link_starts": 0,
    }
    result = challenges.insert_one(doc)
    cid = str(result.inserted_id)
    audit(owner_id, "challenge_created", cid, details=doc["title"])
    return cid


def get_challenge(cid):
    try:
        return challenges.find_one({"_id": ObjectId(cid)})
    except Exception:
        return None


def increment_deep_link_start(cid):
    try:
        challenges.update_one({"_id": ObjectId(cid)}, {"$inc": {"deep_link_starts": 1}})
    except Exception:
        pass


def participant_exists(cid, user_id):
    return participants.find_one({"challenge_id": cid, "user_id": user_id})


def add_participant(cid, user_id, name, residence, photo_file_id, channel_id):
    existing = participant_exists(cid, user_id)
    if existing:
        return existing["number"], False, existing
    counter = challenge_counters.find_one_and_update({"_id": cid}, {"$inc": {"seq": 1}}, upsert=True, return_document=True)
    number = counter["seq"]
    doc = {"challenge_id": cid, "channel_id": channel_id, "user_id": user_id, "number": number, "name": name, "residence": residence, "photo_file_id": photo_file_id, "likes": 0, "stars_received": 0, "liked_by": [], "joined_channel": False, "registered_at": now_utc(), "post_message_id": None}
    try:
        participants.insert_one(doc)
        return number, True, doc
    except Exception:
        existing = participant_exists(cid, user_id)
        if existing:
            return existing["number"], False, existing
        raise


def set_participant_post(cid, number, message_id):
    participants.update_one({"challenge_id": cid, "number": number}, {"$set": {"post_message_id": message_id}})


def set_join_status(cid, user_id, joined):
    participants.update_one({"challenge_id": cid, "user_id": user_id}, {"$set": {"joined_channel": joined}})


def add_like(participant_id, liker_user_id):
    p = participants.find_one({"_id": participant_id})
    if not p or liker_user_id in p.get("liked_by", []):
        return False
    participants.update_one({"_id": participant_id}, {"$inc": {"likes": 1}, "$push": {"liked_by": liker_user_id}})
    return True


def remove_like_on_leave(channel_id, left_user_id):
    for p in participants.find({"channel_id": channel_id, "liked_by": left_user_id}):
        participants.update_one({"_id": p["_id"]}, {"$inc": {"likes": -1}, "$pull": {"liked_by": left_user_id}})


def get_leaderboard(cid, stars_rate=0):
    docs = list(participants.find({"challenge_id": cid}))
    for d in docs:
        d["total_score"] = int(d.get("likes", 0)) + int(d.get("stars_received", 0)) * int(stars_rate or 0)
    docs.sort(key=lambda x: (-x["total_score"], x["number"]))
    return docs


def challenge_stats(cid):
    return {
        "participants": participants.count_documents({"challenge_id": cid}),
        "joined": participants.count_documents({"challenge_id": cid, "joined_channel": True}),
        "likes": sum(int(x.get("likes", 0)) for x in participants.find({"challenge_id": cid}, {"likes": 1})),
        "starts": (get_challenge(cid) or {}).get("deep_link_starts", 0),
    }
