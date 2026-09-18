from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone
from database import challenges, get_leaderboard


def now_utc_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def reminder_text(ch):
    rate = int(ch.get("stars_rate", 0))
    return "🚨 یک ساعت تا پایان چالش!\n\n🔥 رقابت وارد مرحله آخر شده.\n❤️ هنوز فرصت داری لایک بیشتری جمع کنی.\n⭐️ هر Star = {} Like\n🏆 تا آخر ادامه بده!".format(rate)


def ended_text(ch, board):
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 17
    if not board:
        return "🏆🎉 چالش به پایان رسید!\n\n😔 این چالش بدون شرکت‌کننده به پایان رسید.\n\n🚀 منتظر چالش‌های بعدی باشید!"
    lines = []
    count = int(ch.get("winners_count", 0))
    prizes = ch.get("prizes", [])
    for i, p in enumerate(board[:count], 1):
        prize = prizes[i-1] if i-1 < len(prizes) else "-"
        lines.append(f"{medals[i-1]} نفر {i}: {p.get('name','-')}\n🎁 جایزه: {prize}\n🔥 امتیاز: {p.get('total_score',0)}")
    return "🏆🎉 چالش به پایان رسید! 🎉🏆\n\n" + "\n\n".join(lines) + "\n\n🚀 منتظر چالش‌های بعدی باشید!"


async def check_challenges(bot):
    now = now_utc_naive()
    for ch in challenges.find({"active": True}):
        end_time = ch.get("end_time")
        if not end_time:
            continue
        if not ch.get("reminded") and end_time - timedelta(hours=1) <= now < end_time:
            try:
                await bot.send_message(chat_id=ch["channel_id"], text=reminder_text(ch))
            except Exception:
                pass
            challenges.update_one({"_id": ch["_id"], "reminded": {"$ne": True}}, {"$set": {"reminded": True}})
        if now >= end_time:
            # Atomic claim prevents duplicate final messages after a restart.
            claimed = challenges.find_one_and_update({"_id": ch["_id"], "active": True}, {"$set": {"active": False, "ended_at": now}}, return_document=__import__('pymongo').ReturnDocument.BEFORE)
            if not claimed:
                continue
            board = get_leaderboard(str(ch["_id"]), ch.get("stars_rate", 0))
            try:
                await bot.send_message(chat_id=ch["channel_id"], text=ended_text(ch, board))
            except Exception:
                pass


def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_challenges, "interval", minutes=1, args=[bot], id="challenge_checker", replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
