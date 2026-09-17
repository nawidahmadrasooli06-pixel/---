from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime,timedelta
from database import challenges,get_leaderboard

async def check_challenges(bot):
    now=datetime.utcnow()
    for ch in challenges.find({'active':True}):
        end=ch.get('end_time'); start=ch.get('start_time')
        if not end: continue
        if start and now<start: continue
        if not ch.get('reminded') and end-timedelta(hours=1)<=now<end:
            try: await bot.send_message(ch['channel_id'],'⏰ فقط ۱ ساعت تا پایان چالش باقی مانده! ❤️')
            except Exception: pass
            challenges.update_one({'_id':ch['_id']},{'$set':{'reminded':True}})
        if now>=end:
            lb=get_leaderboard(str(ch['_id']),ch.get('stars_rate',0)); lines=['🏆 نتایج نهایی چالش 🏆',f"🎯 {ch.get('title','چالش')}",'']
            if not lb: lines.append('هیچ شرکت‌کننده‌ای ثبت نشده است.')
            else:
                for i,p in enumerate(lb[:ch.get('winners_count',0)]):
                    prize=ch.get('prizes',[])[i] if i<len(ch.get('prizes',[])) else '-'; lines.append(f"{i+1}. {p.get('name','-')} — شماره {p.get('number')} — {p.get('total_score',0)} امتیاز\n🎁 {prize}")
            try: await bot.send_message(ch['channel_id'],'\n'.join(lines))
            except Exception: pass
            challenges.update_one({'_id':ch['_id']},{'$set':{'active':False,'ended_at':now}})

async def start_scheduler(bot):
    scheduler=AsyncIOScheduler(); scheduler.add_job(check_challenges,'interval',minutes=2,args=[bot],id='challenge_checker',replace_existing=True,max_instances=1); scheduler.start(); return scheduler
