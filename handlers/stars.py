from bson import ObjectId
from database import participants, challenges
async def message_reaction_count_update(update,context):
    m=update.message_reaction_count
    if not m: return
    paid=0
    for r in m.reactions:
        if getattr(r.type,"type",None)=="paid": paid=r.total_count; break
    p=participants.find_one({"post_message_id":m.message_id,"channel_id":m.chat.id})
    if not p or not paid: return
    try: ch=challenges.find_one({"_id":ObjectId(p["challenge_id"])})
    except Exception: return
    if not ch or not ch.get("stars_enabled"): return
    participants.update_one({"_id":p["_id"]},{"$set":{"stars_received":paid}})
