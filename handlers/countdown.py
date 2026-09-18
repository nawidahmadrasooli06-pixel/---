from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, timezone
from database import challenges, get_leaderboard


def now_utc_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def reminder_text(ch):
    rate = int(ch.get("stars_rate", 0))
    return (
        "🚨 یک ساعت تا پایان چالش!\n\n"
        "🔥 رقابت وارد آخرین مرحله شد!\n"
        "❤️ هنوز فرصت داری لایک بیشتری جمع کنی.\n"
        f"⭐️ هر Star = {rate} Like\n"
        "🏆 جایزه‌ها منتظر برنده‌ها هستند!\n\n"
        "⏳ فقط 1 ساعت باقی مانده...\n"
        "🚀 تا آخر ادامه بده!"
    )


def ended_text(ch, leaderboard):
    lines = []
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 17
    if not leaderboard:
        winners = "😔 این چالش بدون شرکت‌کننده به پایان رسید."
    else:
        for i, p in enumerate(leaderboard[: int(ch.get("winners_count", 0))], 1):
            prize = ch.get("prizes", [])[i-1] if i-1 < len(ch.get("prizes", [])) else "-"
            lines.append(f"{medals[i-1]} نفر {i}: {p.get('name','-')}\n🎁 جایزه: {prize}\n🔥 امتیاز: {p.get('total_score',0)}")
        winners = "\n\n".join(lines)
    return "🏆🎉 چالش به پایان رسید! 🎉🏆\n\n❤️ ممنون از تمام شرکت‌کننده‌ها!\n\n" + winners + "\n\n🎉 تبریک به برنده‌ها!\n🚀 منتظر چالش‌های بعدی باشید!"


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
            challenges.update_one({"_id": ch["_id"]}, {"$set": {"reminded": True}})
        if now >= end_time:
            leaderboard = get_leaderboard(str(ch["_id"]), ch.get("stars_rate", 0))
            try:
                await bot.send_message(chat_id=ch["channel_id"], text=ended_text(ch, leaderboard))
            except Exception:
                pass
            challenges.update_one({"_id": ch["_id"]}, {"$set": {"active": False, "ended_at": now}})


async def start_scheduler(bot):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_challenges, "interval", minutes=1, args=[bot], id="challenge_checker", replace_existing=True, max_instances=1, coalesce=True)
    scheduler.start()
    return scheduler
