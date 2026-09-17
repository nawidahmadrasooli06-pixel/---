from database import participants, challenges

def _paid_count(mrc):
    total=0
    for reaction in (mrc.reactions or []):
        rtype=getattr(reaction.type,"type",None)
        if rtype=="paid": total += int(reaction.total_count or 0)
    return total

async def message_reaction_count_update(update, context):
    mrc=update.message_reaction_count
    if not mrc: return
    p=participants.find_one({"post_message_id":mrc.message_id,"channel_id":mrc.chat.id})
    if not p: return
    ch=challenges.find_one({"_id":__import__('bson').ObjectId(p['challenge_id'])})
    if not ch or not ch.get('stars_enabled'): return
    paid=_paid_count(mrc)
    participants.update_one({'_id':p['_id']},{'$set':{'stars_received':paid}})
