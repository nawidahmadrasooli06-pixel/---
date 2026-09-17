from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from database import challenges, get_leaderboard

scheduler = AsyncIOScheduler()

async def check_challenges(bot):
    now = datetime.utcnow()
    for ch in challenges.find({"active": True}):
        end_time = ch["end_time"]
        remind_time = end_time - timedelta(hours=1)

        if not ch.get("reminded") and remind_time <= now < end_time:
            await bot.send_message(
                chat_id=ch["channel_id"],
                text="⏰ فقط ۱ ساعت تا پایان چالش مونده! کوشا باشید 🥹❤️"
            )
            challenges.update_one({"_id": ch["_id"]}, {"$set": {"reminded": True}})

        if now >= end_time:
            leaderboard = get_leaderboard(str(ch["_id"]), ch.get("stars_rate", 0))
            if not leaderboard:
                text = "چالش تموم شد، ولی شرکت‌کننده‌ای ثبت نشد."
            else:
                lines = ["🏆 نتایج نهایی چالش 🏆\n"]
                for i, p in enumerate(leaderboard[:ch["winners_count"]]):
                    prize = ch["prizes"][i] if i < len(ch["prizes"]) else "-"
                    lines.append(f"{i+1}. {p['name']} (شماره {p['number']}) — {p['total_score']} امتیاز — جایزه: {prize}")
                text = "\n".join(lines)
            await bot.send_message(chat_id=ch["channel_id"], text=text)
            challenges.update_one({"_id": ch["_id"]}, {"$set": {"active": False}})

def start_scheduler(bot):
    scheduler.add_job(check_challenges, "interval", minutes=2, args=[bot])
    scheduler.start()
