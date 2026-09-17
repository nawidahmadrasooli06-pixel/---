from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import challenges,get_leaderboard

def as_utc(dt):
    if dt.tzinfo is None: return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
async def check_challenges(bot):
    now=datetime.now(timezone.utc)
    for ch in challenges.find({"active":True}):
        end=as_utc(ch["end_time"]); start=as_utc(ch.get("start_time",now));
        if not ch.get("reminded") and end-timedelta(hours=1)<=now<end:
            try: await bot.send_message(ch["channel_id"],"⏰ فقط ۱ ساعت تا پایان چالش باقی مانده! موفق باشید ❤️")
            except Exception: pass
            challenges.update_one({"_id":ch["_id"]},{"$set":{"reminded":True}})
        if now>=end:
            board=get_leaderboard(str(ch["_id"]),ch.get("stars_rate",0)); lines=[f"🏆 نتایج نهایی: {ch.get('title','چالش')}\n"]
            if not board: lines.append("شرکت‌کننده‌ای ثبت نشد.")
            else:
                for i,p in enumerate(board[:ch.get("winners_count",1)]):
                    prize=ch.get("prizes",[])[i] if i<len(ch.get("prizes",[])) else "-"
                    lines.append(f"{i+1}. {p['name']} — شماره {p['number']} — {p['total_score']} امتیاز\n🎁 {prize}")
            try: await bot.send_message(ch["channel_id"],"\n".join(lines))
            except Exception: pass
            challenges.update_one({"_id":ch["_id"]},{"$set":{"active":False,"ended_at":now}})
async def start_scheduler(bot):
    s=AsyncIOScheduler(); s.add_job(check_challenges,"interval",minutes=2,args=[bot],id="challenge_checker",replace_existing=True,max_instances=1); s.start(); return s
