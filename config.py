import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
MONGO_URI = os.getenv("MONGO_URI", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set")
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID is not set")
