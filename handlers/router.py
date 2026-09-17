from handlers.owner import receive_title,receive_channel,receive_owner_username,receive_winners_count,receive_prize,receive_manual_date,receive_time,receive_duration,receive_rules,receive_stars_rate
from handlers.participant import receive_name,receive_age,receive_city,receive_photo,receive_report_text

async def text_router(update,context):
    state=context.user_data.get("state")
    handlers={"owner_title":receive_title,"owner_channel":receive_channel,"owner_username":receive_owner_username,"owner_winners":receive_winners_count,"owner_prize":receive_prize,"owner_manual_date":receive_manual_date,"owner_time":receive_time,"owner_duration":receive_duration,"owner_rules":receive_rules,"owner_stars_rate":receive_stars_rate,"await_name":receive_name,"await_age":receive_age,"await_city":receive_city,"await_report_text":receive_report_text}
    fn=handlers.get(state)
    if fn: await fn(update,context)

async def photo_router(update,context):
    if context.user_data.get("state")=="await_photo": await receive_photo(update,context)
