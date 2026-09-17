from lang import t
async def about_callback(update,context):
    q=update.callback_query; await q.answer(); await q.message.reply_text(t(context.user_data.get("lang","fa"),"about_text"))
async def creator_callback(update,context):
    q=update.callback_query; await q.answer(); await q.message.reply_text(t(context.user_data.get("lang","fa"),"creator_text"))
