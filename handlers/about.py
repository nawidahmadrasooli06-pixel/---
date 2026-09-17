from lang import t
from handlers.start import main_menu_keyboard
async def about_callback(update,context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa"); await q.message.reply_text(t(lang,"about_text"),reply_markup=main_menu_keyboard(lang))
async def creator_callback(update,context):
    q=update.callback_query; await q.answer(); lang=context.user_data.get("lang","fa"); await q.message.reply_text(t(lang,"creator_text"),reply_markup=main_menu_keyboard(lang))
