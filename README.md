# Challenge Bot — stable Render build

Start command:
`python main.py`

Required Render environment variables:
- `BOT_TOKEN`
- `MONGO_URI`
- `ADMIN_ID`

The MongoDB URI and bot token are intentionally read only from environment variables.
Do not put secrets in GitHub.

Features:
- Compact editable inline main menu
- Persistent Telegram Start command/menu button
- Persian / English UI
- Challenge-specific deep-link registration
- Name, age, city/province and profile photo
- Channel-link validation and bot-admin check
- Afghanistan / Iran / Germany timezone handling
- Gregorian / Jalali dates and human-friendly times
- Like tracking with membership and one-like-per-user protection
- Paid Telegram Stars reaction count tracking
- Participant and owner statistics
- Report system routed to Super Admin
- Automatic one-hour reminder and final results
- Render health endpoint
- MongoDB indexes and atomic participant numbering
