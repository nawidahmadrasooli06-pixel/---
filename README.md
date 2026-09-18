# Challenge Bot — Final

Render Start Command:
`python main.py`

Required environment variables:
- `BOT_TOKEN`
- `MONGO_URI`
- `ADMIN_ID`

`handlers/__init__.py` is intentionally empty.

## Final features
- Separate deep-link registration for every challenge
- Participant name, age, city/province and profile photo
- Unique participant number per challenge
- Clean challenge and participant banners
- Active-challenge discovery
- Participant statistics per active challenge
- Owner statistics per active challenge
- Channel membership tracking
- Like tracking with one-like-per-user protection
- Star reaction count updates through Telegram `message_reaction_count`
- Afghanistan / Iran / Germany time zones
- Human-friendly date and time entry
- Automatic challenge reminder and final results
- Report system routed to Super Admin
- Persian and English UI
- Render health server and polling setup
