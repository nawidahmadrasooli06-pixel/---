from telegram import InlineKeyboardButton,InlineKeyboardMarkup
from config import ADMIN_ID
from database import users,challenges,participants,reports,audit
from lang import t

async def admin_panel(update,context):
    if update.effective_user.id!=ADMIN_ID: await update.effective_message.reply_text(t(context.user_data.get('lang','fa'),'admin_only')); return
    lang=context.user_data.get('lang','fa'); await update.effective_message.reply_text(t(lang,'admin_panel'),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('📊 آمار کل',callback_data='admin_stats'),InlineKeyboardButton('🚨 گزارش‌ها',callback_data='admin_reports')]]))

async def admin_callback(update,context):
    q=update.callback_query; await q.answer()
    if q.from_user.id!=ADMIN_ID:return
    lang=context.user_data.get('lang','fa')
    if q.data=='admin_stats': await q.message.reply_text(t(lang,'admin_stats',users=users.count_documents({}),challenges=challenges.count_documents({}),active=challenges.count_documents({'active':True}),participants=participants.count_documents({}),reports=reports.count_documents({'status':'open'})))
    elif q.data=='admin_reports':
        docs=list(reports.find({'status':'open'}).sort('created_at',-1).limit(20))
        if not docs: await q.message.reply_text(t(lang,'no_reports')); return
        for r in docs:
            ch=challenges.find_one({'_id':__import__('bson').ObjectId(r['challenge_id'])}); text=t(lang,'report_item',id=str(r['_id'])[-6:],user=r['reporter_id'],title=(ch or {}).get('title','-'),reason=r['reason'],text=r.get('text',''))
            await q.message.reply_text(text,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('✅ بستن گزارش',callback_data=f"close_report_{r['_id']}")]]))

async def close_report_callback(update,context):
    q=update.callback_query; await q.answer()
    if q.from_user.id!=ADMIN_ID:return
    rid=q.data.split('_',2)[2]; reports.update_one({'_id':__import__('bson').ObjectId(rid)},{'$set':{'status':'closed'}}); await q.message.edit_reply_markup(reply_markup=None); await q.message.reply_text(t(context.user_data.get('lang','fa'),'report_closed'))

async def stats_command(update,context):
    if update.effective_user.id!=ADMIN_ID:return
    await update.message.reply_text(t(context.user_data.get('lang','fa'),'admin_stats',users=users.count_documents({}),challenges=challenges.count_documents({}),active=challenges.count_documents({'active':True}),participants=participants.count_documents({}),reports=reports.count_documents({'status':'open'})))

async def block_command(update,context):
    if update.effective_user.id!=ADMIN_ID:return
    if not context.args: await update.message.reply_text(t(context.user_data.get('lang','fa'),'block_usage')); return
    uid=int(context.args[0]); users.update_one({'user_id':uid},{'$set':{'blocked':True}},upsert=True); audit(ADMIN_ID,'block_user',target_user_id=uid); await update.message.reply_text(t(context.user_data.get('lang','fa'),'blocked'))

async def unblock_command(update,context):
    if update.effective_user.id!=ADMIN_ID:return
    if not context.args: return
    uid=int(context.args[0]); users.update_one({'user_id':uid},{'$set':{'blocked':False}},upsert=True); audit(ADMIN_ID,'unblock_user',target_user_id=uid); await update.message.reply_text(t(context.user_data.get('lang','fa'),'unblocked'))
