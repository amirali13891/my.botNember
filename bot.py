# -*- coding: utf-8 -*-
"""
Virtual Number Sales Bot — Final (Colored Buttons + Report Channel)
"""
import asyncio, logging, os, re
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

load_dotenv()

# ════════════════ CONFIG ════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "").strip()
TG_API_ID = int(os.getenv("TG_API_ID", "0") or 0)
TG_API_HASH = os.getenv("TG_API_HASH", "").strip()
MAIN_CHANNEL_LINK = os.getenv("MAIN_CHANNEL_LINK", "").strip()
REPORT_CHANNEL_ID = os.getenv("REPORT_CHANNEL_ID", "").strip()
REPORT_CHANNEL_LINK = os.getenv("REPORT_CHANNEL_LINK", "").strip()
GUIDE_CHANNEL_LINK = os.getenv("GUIDE_CHANNEL_LINK", "").strip()
DEFAULT_ADMINS = os.getenv("DEFAULT_ADMINS", "").strip()
RESERVE_MIN = int(os.getenv("RESERVE_MINUTES", "10") or 10)
DB_PATH = os.getenv("DB_PATH", "bot.db")

REPORT_CHANNEL = None
if REPORT_CHANNEL_ID:
    if REPORT_CHANNEL_ID.lstrip("-").isdigit():
        REPORT_CHANNEL = int(REPORT_CHANNEL_ID)
    elif REPORT_CHANNEL_ID.startswith("@"):
        REPORT_CHANNEL = REPORT_CHANNEL_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("vbot")
router = Router()
pending_logins = {}

# ════════════════ I18N ════════════════
T = {
    "fa": {
        "welcome": "👋 سلام <b>{name}</b>!\nبه ربات فروش شماره مجازی خوش آمدید.\nاز منوی زیر انتخاب کنید:",
        "profile_title": "👤 <b>حساب کاربری</b>",
        "profile_body": ("🆔 شناسه عددی: <code>{uid}</code>\n"
                         "💰 موجودی: <b>{balance:,}</b> تومان\n"
                         "🕒 ساعت: <code>{time}</code>\n"
                         "🛒 تعداد خریدها: <b>{purchases}</b>\n"
                         "💳 مجموع شارژ: <b>{charged:,}</b> تومان"),
        "support": "🎧 <b>پشتیبانی</b>\n\nبرای ارتباط با پشتیبانی به آیدی‌های زیر پیام دهید:\n{ids}\n\nممنون که با ما هستید 🌹",
        "buy_title": "🛒 <b>خرید شماره مجازی</b>\nلطفاً یک دسته‌بندی انتخاب کنید:",
        "cat_scam": "🚫 اکانت اسکم", "cat_fake": "🎭 اکانت جعلی",
        "cat_ready": "✅ اکانت آماده نوریپ", "cat_rep_daily": "♻️ اکانت ریپ دایم",
        "cat_empty": "❌ در این دسته فعلاً پنلی ثبت نشده.",
        "panel_list": "📦 پنل‌های موجود در دسته <b>{cat}</b>:",
        "account_list": "📞 شماره‌های موجود در پنل <b>{panel}</b>\nقیمت: <b>{price:,}</b> تومان\n\nیکی را انتخاب کنید:",
        "no_accounts": "😔 در این پنل موجودی نیست.",
        "reserved": "🔒 این شماره برای شما رزرو شد (تا {minutes} دقیقه).\n\n💳 لطفاً مبلغ <b>{price:,}</b> تومان به کارت زیر واریز کنید:\n\n<code>{card}</code>\n\nسپس دکمه <b>ارسال رسید</b> را بزنید.",
        "no_card": "⚠️ برای این فروشنده کارتی ثبت نشده. با پشتیبانی تماس بگیرید.",
        "send_receipt": "📸 لطفاً عکس رسید پرداخت را ارسال کنید.",
        "receipt_sent": "✅ رسید شما برای بررسی ارسال شد.\nبه محض تایید، اکانت به شما تحویل داده می‌شود.",
        "approved_buyer": "🎉 رسید شما تایید شد!\n\n📱 شماره: <code>{phone}</code>\n🔐 رمز دو مرحله‌ای: <code>{twofa}</code>\n\nبرای دریافت کد ورود، دکمه «دریافت کد» را بزنید.",
        "rejected_buyer": "❌ رسید شما رد شد. اگر اشتباهی بوده با پشتیبانی در تماس باشید.",
        "get_code_btn": "🔑 دریافت کد",
        "get_code_wait": "⏳ در حال دریافت کد از تلگرام...",
        "get_code_ok": "🔑 کد ورود شما: <code>{code}</code>{twofa}",
        "get_code_fail": "⚠️ کدی یافت نشد. ابتدا در اپ تلگرام شماره را وارد کنید تا کد ارسال شود، سپس دوباره تلاش کنید.",
        "twofa_line": "\n🔐 رمز دو مرحله‌ای: <code>{pw}</code>",
        "logout_ok": "🚪 از ربات خارج شدید.\nنشست‌های ربات از اکانت‌های خریداری‌شده شما قطع شد.",
        "add_acc_choose_panel": "➕ <b>افزودن شماره</b>\nیک پنل انتخاب کنید:",
        "add_acc_phone": "📱 شماره را با فرمت بین‌المللی ارسال کنید (مثلاً +989121234567):",
        "add_acc_code": "📨 کد ارسال شده را وارد کنید:",
        "add_acc_2fa": "🔐 رمز دو مرحله‌ای را وارد کنید:",
        "add_acc_ok": "✅ اکانت با موفقیت اضافه شد!",
        "add_acc_err": "❌ خطا در افزودن اکانت:\n<code>{err}</code>",
        "add_panel_name": "🏷 نام پنل را وارد کنید (مثلاً: America 2024):",
        "add_panel_price": "💰 قیمت (تومان) را وارد کنید:",
        "add_panel_cat": "📂 دسته‌بندی را انتخاب کنید:",
        "add_panel_flag": "🌍 فلگ کشور را وارد کنید (مثلاً 🇺🇸):",
        "add_panel_ok": "✅ پنل ایجاد شد.",
        "add_admin_id": "👤 آیدی عددی ادمین جدید را ارسال کنید:",
        "add_admin_ok": "✅ ادمین اضافه شد.",
        "add_admin_fail": "❌ فقط مالک می‌تواند ادمین اضافه کند.",
        "card_prompt": "💳 شماره کارت خود را ارسال کنید:",
        "card_ok": "✅ کارت شما ذخیره شد.",
        "owner_only": "⛔ فقط مالک.",
        "admin_only": "⛔ دسترسی ندارید.",
        "balance_low": "❌ موجودی کافی نیست.\n💰 موجودی: <b>{bal:,}</b> تومان\n💵 نیاز: <b>{need:,}</b> تومان\n\nجهت شارژ با پشتیبانی تماس بگیرید.",
        "back": "◀️ بازگشت", "cancel": "❌ انصراف", "home": "🏠 منوی اصلی",
        "btn_profile": "👤 حساب کاربری", "btn_support": "🎧 پشتیبانی",
        "btn_buy": "🛒 خرید شماره مجازی", "btn_guide": "📚 توضیحات",
        "btn_report": "📣 گزارش خرید", "btn_main_channel": "🏪 چنل اصلی",
        "btn_lang": "🌐 تغییر زبان", "btn_logout": "🚪 خروج",
        "btn_add_account": "➕ افزودن شماره", "btn_add_panel": "📦 افزودن پنل",
        "btn_add_admin": "👑 افزودن ادمین", "btn_set_card": "💳 تنظیم کارت",
        "btn_receipt": "📸 ارسال رسید",
        "guide_msg": "📚 برای مشاهده آموزش‌ها روی دکمه زیر بزنید:",
        "report_msg": "📣 برای مشاهده گزارش خریدها روی دکمه زیر بزنید:",
        "open_channel": "🔗 ورود به کانال",
        "order_new": "🛒 سفارش جدید\nخریدار: <code>{uid}</code>\nپنل: {panel}\nشماره: <code>{phone}</code>\nمبلغ: {amount:,} تومان",
        "order_approved_seller": "✅ سفارش تایید شد.",
        "order_rejected_seller": "❌ سفارش رد شد.",
        "approve": "✅ تایید", "reject": "❌ رد",
        "lang_set": "✅ زبان تنظیم شد.",
        "invalid": "❌ مقدار نامعتبر.",
        "cat_display": {"scam": "🚫 اسکم", "fake": "🎭 جعلی", "ready": "✅ نوریپ", "rep": "♻️ ریپ دایم"},
        "report_text": ("✅ <b>گزارش خرید موفق</b>\n\n"
                        "▫️ شناسه خریدار: <code>{uid}</code>\n"
                        "▫️ کشور: {flag}\n"
                        "▫️ پنل: <b>{panel}</b>\n"
                        "🔸 شماره خریداری شده: <code>{phone}</code>\n"
                        "▫️ مبلغ پرداخت شده: <b>{amount:,}</b> تومان\n"
                        "▫️ تاریخ خرید: <code>{date}</code>\n\n"
                        "📣 شما نیز می‌توانید با استفاده از دکمه زیر وارد بخش خرید شماره شوید."),
        "buy_from_channel": "🛒 خرید شماره مجازی",
        "photo_set": "✅ عکس پنل ذخیره شد.",
        "photo_missing": "❌ عکس را به عنوان ریپلای روی این پیام بفرستید.",
    },
    "en": {
        "welcome": "👋 Hi <b>{name}</b>!\nWelcome to the Virtual Number Store.\nUse the menu below:",
        "profile_title": "👤 <b>Account</b>",
        "profile_body": ("🆔 User ID: <code>{uid}</code>\n"
                         "💰 Balance: <b>{balance:,}</b> Toman\n"
                         "🕒 Time: <code>{time}</code>\n"
                         "🛒 Purchases: <b>{purchases}</b>\n"
                         "💳 Total Charged: <b>{charged:,}</b> Toman"),
        "support": "🎧 <b>Support</b>\n\nPlease contact our staff:\n{ids}\n\nThank you 🌹",
        "buy_title": "🛒 <b>Buy Virtual Number</b>\nPick a category:",
        "cat_scam": "🚫 Scam Account", "cat_fake": "🎭 Fake Account",
        "cat_ready": "✅ Ready Non-rep", "cat_rep_daily": "♻️ Rep Daily",
        "cat_empty": "❌ No panels in this category yet.",
        "panel_list": "📦 Panels in <b>{cat}</b>:",
        "account_list": "📞 Numbers in <b>{panel}</b>\nPrice: <b>{price:,}</b> Toman\n\nPick one:",
        "no_accounts": "😔 No stock in this panel.",
        "reserved": "🔒 Reserved for you ({minutes} min).\n\n💳 Please pay <b>{price:,}</b> Toman to:\n\n<code>{card}</code>\n\nThen press <b>Send Receipt</b>.",
        "no_card": "⚠️ No card registered for this seller. Contact support.",
        "send_receipt": "📸 Please send the receipt photo.",
        "receipt_sent": "✅ Receipt sent for review.\nYou'll receive the account once approved.",
        "approved_buyer": "🎉 Receipt approved!\n\n📱 Phone: <code>{phone}</code>\n🔐 2FA: <code>{twofa}</code>\n\nPress «Get Code» to receive login code.",
        "rejected_buyer": "❌ Receipt rejected. Contact support if this was a mistake.",
        "get_code_btn": "🔑 Get Code",
        "get_code_wait": "⏳ Fetching code...",
        "get_code_ok": "🔑 Login code: <code>{code}</code>{twofa}",
        "get_code_fail": "⚠️ No code found. First enter the number in Telegram to request a code, then try again.",
        "twofa_line": "\n🔐 2FA: <code>{pw}</code>",
        "logout_ok": "🚪 Logged out.\nBot sessions for your purchased accounts terminated.",
        "add_acc_choose_panel": "➕ <b>Add Account</b>\nChoose a panel:",
        "add_acc_phone": "📱 Send phone in international format (e.g. +989121234567):",
        "add_acc_code": "📨 Enter the code sent:",
        "add_acc_2fa": "🔐 Enter 2FA password:",
        "add_acc_ok": "✅ Account added!",
        "add_acc_err": "❌ Error adding account:\n<code>{err}</code>",
        "add_panel_name": "🏷 Enter panel name (e.g. America 2024):",
        "add_panel_price": "💰 Enter price (Toman):",
        "add_panel_cat": "📂 Select category:",
        "add_panel_flag": "🌍 Enter flag (e.g. 🇺🇸):",
        "add_panel_ok": "✅ Panel created.",
        "add_admin_id": "👤 Enter new admin numeric ID:",
        "add_admin_ok": "✅ Admin added.",
        "add_admin_fail": "❌ Only owner can add admins.",
        "card_prompt": "💳 Send your card number:",
        "card_ok": "✅ Card saved.",
        "owner_only": "⛔ Owner only.", "admin_only": "⛔ Access denied.",
        "balance_low": "❌ Insufficient balance.\n💰 Balance: <b>{bal:,}</b>\n💵 Needed: <b>{need:,}</b>\n\nContact support to top up.",
        "back": "◀️ Back", "cancel": "❌ Cancel", "home": "🏠 Main Menu",
        "btn_profile": "👤 Account", "btn_support": "🎧 Support",
        "btn_buy": "🛒 Buy Virtual Number", "btn_guide": "📚 Guide",
        "btn_report": "📣 Purchase Report", "btn_main_channel": "🏪 Main Channel",
        "btn_lang": "🌐 Language", "btn_logout": "🚪 Logout",
        "btn_add_account": "➕ Add Account", "btn_add_panel": "📦 Add Panel",
        "btn_add_admin": "👑 Add Admin", "btn_set_card": "💳 Set Card",
        "btn_receipt": "📸 Send Receipt",
        "guide_msg": "📚 Join our channel for guides:",
        "report_msg": "📣 Join our channel to see purchase reports:",
        "open_channel": "🔗 Open Channel",
        "order_new": "🛒 New Order\nBuyer: <code>{uid}</code>\nPanel: {panel}\nNumber: <code>{phone}</code>\nAmount: {amount:,} Toman",
        "order_approved_seller": "✅ Order approved.",
        "order_rejected_seller": "❌ Order rejected.",
        "approve": "✅ Approve", "reject": "❌ Reject",
        "lang_set": "✅ Language set.", "invalid": "❌ Invalid value.",
        "cat_display": {"scam": "🚫 Scam", "fake": "🎭 Fake", "ready": "✅ Ready", "rep": "♻️ Rep Daily"},
        "report_text": ("✅ <b>Successful Purchase Report</b>\n\n"
                        "▫️ Buyer ID: <code>{uid}</code>\n"
                        "▫️ Country: {flag}\n"
                        "▫️ Panel: <b>{panel}</b>\n"
                        "🔸 Purchased Number: <code>{phone}</code>\n"
                        "▫️ Paid: <b>{amount:,}</b> Toman\n"
                        "▫️ Date: <code>{date}</code>\n\n"
                        "📣 You can also enter the purchase section using the button below."),
        "buy_from_channel": "🛒 Buy Virtual Number",
        "photo_set": "✅ Panel photo saved.",
        "photo_missing": "❌ Reply to this message with a photo.",
    },
}

def t(lang: str, key: str) -> str:
    return T.get(lang, T["fa"]).get(key, key)

# ════════════════ DB ════════════════
class DB:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'fa',
                balance INTEGER DEFAULT 0, total_charged INTEGER DEFAULT 0,
                purchases INTEGER DEFAULT 0, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS admins(
                user_id INTEGER PRIMARY KEY, username TEXT,
                added_by INTEGER, added_at TEXT
            );
            CREATE TABLE IF NOT EXISTS panels(
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                price INTEGER NOT NULL, category TEXT NOT NULL,
                flag TEXT DEFAULT '🌍', created_by INTEGER, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, panel_id INTEGER NOT NULL,
                phone TEXT, session TEXT, twofa TEXT, status TEXT DEFAULT 'available',
                reserved_by INTEGER, reserved_until TEXT, sold_to INTEGER, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                account_id INTEGER, panel_id INTEGER, amount INTEGER,
                status TEXT DEFAULT 'pending', receipt_file_id TEXT, created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY, value TEXT
            );
            """)
            await db.commit()

    async def get_user(self, uid: int) -> dict:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if row is None:
                await db.execute("INSERT INTO users(user_id, created_at) VALUES(?,?)",
                                 (uid, datetime.now(timezone.utc).isoformat()))
                await db.commit()
                cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
                row = await cur.fetchone()
            return dict(row)

    async def set_lang(self, uid: int, lang: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))
            await db.commit()

    async def is_admin(self, uid: int) -> bool:
        if uid == OWNER_ID: return True
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,))
            return await cur.fetchone() is not None

    async def add_admin(self, uid: int, username: str = "", by: int = 0):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO admins(user_id, username, added_by, added_at) VALUES(?,?,?,?)",
                (uid, username, by, datetime.now(timezone.utc).isoformat()))
            await db.commit()

    async def all_admins(self) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT user_id, username FROM admins ORDER BY added_at ASC")
            return [dict(r) for r in await cur.fetchall()]

    async def add_balance(self, uid: int, amount: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE users SET balance=balance+?, total_charged=total_charged+? WHERE user_id=?",
                (amount, amount, uid))
            await db.commit()

    async def inc_purchases(self, uid: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET purchases=purchases+1 WHERE user_id=?", (uid,))
            await db.commit()

    async def deduct_balance(self, uid: int, amount: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row or row["balance"] < amount: return False
            await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amount, uid))
            await db.commit()
            return True

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
            row = await cur.fetchone()
            return row[0] if row else default

    async def set_setting(self, key: str, value: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))
            await db.commit()

    async def create_panel(self, name, price, category, flag, by) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO panels(name, price, category, flag, created_by, created_at) VALUES(?,?,?,?,?,?)",
                (name, price, category, flag, by, datetime.now(timezone.utc).isoformat()))
            await db.commit()
            return cur.lastrowid

    async def panels_by_cat(self, category) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM panels WHERE category=? ORDER BY id DESC", (category,))
            return [dict(r) for r in await cur.fetchall()]

    async def all_panels(self) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM panels ORDER BY id DESC")
            return [dict(r) for r in await cur.fetchall()]

    async def get_panel(self, pid) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM panels WHERE id=?", (pid,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def add_account(self, pid, phone, session, twofa="") -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO accounts(panel_id, phone, session, twofa, created_at) VALUES(?,?,?,?,?)",
                (pid, phone, session, twofa, datetime.now(timezone.utc).isoformat()))
            await db.commit()
            return cur.lastrowid

    async def available_accounts(self, panel_id) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """SELECT * FROM accounts WHERE panel_id=? AND status='available'
                   AND (reserved_until IS NULL OR reserved_until < ?) ORDER BY id ASC""",
                (panel_id, now))
            return [dict(r) for r in await cur.fetchall()]

    async def get_account(self, aid) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM accounts WHERE id=?", (aid,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def reserve_account(self, aid, uid, minutes=None):
        minutes = minutes or RESERVE_MIN
        until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE accounts SET reserved_by=?, reserved_until=? WHERE id=? AND status='available'",
                (uid, until, aid))
            await db.commit()

    async def extend_reservation(self, aid, hours=24):
        until = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE accounts SET reserved_until=? WHERE id=?", (until, aid))
            await db.commit()

    async def release_account(self, aid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE accounts SET reserved_by=NULL, reserved_until=NULL WHERE id=? AND status='available'",
                (aid,))
            await db.commit()

    async def sell_account(self, aid, uid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE accounts SET status='sold', sold_to=?, reserved_by=NULL, reserved_until=NULL WHERE id=?",
                (uid, aid))
            await db.commit()

    async def user_accounts(self, uid) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM accounts WHERE sold_to=?", (uid,))
            return [dict(r) for r in await cur.fetchall()]

    async def clear_user_sessions(self, uid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE accounts SET session=NULL WHERE sold_to=?", (uid,))
            await db.commit()

    async def create_order(self, uid, aid, pid, amount) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                "INSERT INTO orders(user_id, account_id, panel_id, amount, status, created_at) VALUES(?,?,?,?,'pending',?)",
                (uid, aid, pid, amount, datetime.now(timezone.utc).isoformat()))
            await db.commit()
            return cur.lastrowid

    async def set_order_receipt(self, oid, file_id):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE orders SET receipt_file_id=? WHERE id=?", (file_id, oid))
            await db.commit()

    async def get_order(self, oid) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM orders WHERE id=?", (oid,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def approve_order(self, oid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE orders SET status='approved' WHERE id=?", (oid,))
            await db.commit()

    async def reject_order(self, oid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE orders SET status='rejected' WHERE id=?", (oid,))
            await db.commit()

db = DB(DB_PATH)

# ════════════════ BUTTONS (Colored) ════════════════
def B(text: str, cb: Optional[str] = None, url: Optional[str] = None, style: Optional[str] = None) -> InlineKeyboardButton:
    kw = {"text": text}
    if cb is not None: kw["callback_data"] = cb
    if url is not None: kw["url"] = url
    if style is not None:
        try:
            kw["style"] = style
            return InlineKeyboardButton(**kw)
        except TypeError:
            # Fallback for older versions
            kw.pop("style")
            return InlineKeyboardButton(**kw)
    return InlineKeyboardButton(**kw)

def KB(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ════════════════ STATES ════════════════
class S(StatesGroup):
    acc_panel = State(); acc_phone = State(); acc_code = State(); acc_2fa = State()
    p_name = State(); p_price = State(); p_cat = State(); p_flag = State()
    a_id = State(); card = State(); receipt = State()

# ════════════════ HELPERS ════════════════
async def get_lang(uid): 
    u = await db.get_user(uid); return u.get("lang", "fa") or "fa"

def mask_phone(p: str) -> str:
    if len(p) <= 8: return p
    return p[:5] + "***" + p[-3:]

def now_str() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")

async def get_support_ids(lang: str) -> str:
    lines = []
    owner_disp = OWNER_USERNAME or f"<code>{OWNER_ID}</code>"
    lines.append(f"• {'Owner' if lang=='en' else 'مالک'}: {owner_disp}")
    for a in await db.all_admins():
        disp = a["username"] or f"<code>{a['user_id']}</code>"
        lines.append(f"• {'Admin' if lang=='en' else 'ادمین'}: {disp}")
    return "\n".join(lines)

async def notify_admins(bot: Bot, text: str, kb=None, photo=None):
    targets = {OWNER_ID}
    for a in await db.all_admins():
        targets.add(a["user_id"])
    for uid in targets:
        try:
            if photo:
                await bot.send_photo(uid, photo, caption=text, reply_markup=kb)
            else:
                await bot.send_message(uid, text, reply_markup=kb)
        except Exception as e:
            log.warning(f"notify {uid} failed: {e}")

# ════════════════ KEYBOARDS ════════════════
async def main_menu_kb(uid: int, lang: str) -> InlineKeyboardMarkup:
    is_admin = await db.is_admin(uid)
    rows = [
        [B(t(lang,"btn_profile"), cb="profile", style="primary"), B(t(lang,"btn_support"), cb="support", style="primary")],
        [B(t(lang,"btn_buy"), cb="buy", style="success")],
        [B(t(lang,"btn_guide"), cb="guide", style="primary"), B(t(lang,"btn_report"), cb="report", style="primary")],
    ]
    row_ch = []
    if MAIN_CHANNEL_LINK:
        row_ch.append(B(t(lang,"btn_main_channel"), url=MAIN_CHANNEL_LINK, style="primary"))
    row_ch.append(B(t(lang,"btn_lang"), cb="lang", style="primary"))
    rows.append(row_ch)
    rows.append([B(t(lang,"btn_logout"), cb="logout", style="danger")])
    if is_admin:
        rows.append([B(t(lang,"btn_add_account"), cb="acc_add", style="success"), B(t(lang,"btn_add_panel"), cb="panel_add", style="success")])
        rows.append([B(t(lang,"btn_set_card"), cb="set_card", style="success")])
        if uid == OWNER_ID:
            rows.append([B(t(lang,"btn_add_admin"), cb="admin_add", style="danger")])
    return KB(rows)

def back_kb(lang, cb="home"):
    return KB([[B(t(lang,"back"), cb=cb, style="danger")]])

def categories_kb(lang):
    cd = t(lang,"cat_display")
    return KB([
        [B(cd["scam"], cb="cat:scam", style="danger")],
        [B(cd["fake"], cb="cat:fake", style="danger")],
        [B(cd["ready"], cb="cat:ready", style="success")],
        [B(cd["rep"], cb="cat:rep", style="success")],
        [B(t(lang,"back"), cb="home", style="primary")],
    ])

async def panels_kb(lang, category):
    panels = await db.panels_by_cat(category)
    rows = [[B(f"{p['flag']} {p['name']} — {p['price']:,}", cb=f"panel:{p['id']}", style="primary")] for p in panels]
    rows.append([B(t(lang,"back"), cb="buy", style="danger")])
    return KB(rows)

async def accounts_kb(lang, pid):
    accs = await db.available_accounts(pid)
    rows = [[B(a["phone"], cb=f"acc:{a['id']}", style="success")] for a in accs]
    rows.append([B(t(lang,"back"), cb=f"cat_of:{pid}", style="danger")])
    return KB(rows)

def receipt_kb(lang, oid):
    return KB([
        [B(t(lang,"btn_receipt"), cb=f"receipt:{oid}", style="success")],
        [B(t(lang,"cancel"), cb=f"cancel:{oid}", style="danger")],
    ])

def approve_kb(oid):
    return KB([[B("✅ تایید", cb=f"ap:approve:{oid}", style="success"), B("❌ رد", cb=f"ap:reject:{oid}", style="danger")]])

# ════════════════ HANDLERS ════════════════
@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await db.get_user(m.from_user.id)
    lang = await get_lang(m.from_user.id)
    text = t(lang,"welcome").format(name=m.from_user.first_name or "User")
    kb = await main_menu_kb(m.from_user.id, lang)
    photo = await db.get_setting("panel_photo")
    if photo:
        try:
            await m.answer_photo(photo, caption=text, reply_markup=kb)
            return
        except Exception: pass
    await m.answer(text, reply_markup=kb)

@router.message(Command("help"))
async def cmd_help(m: Message):
    lang = await get_lang(m.from_user.id)
    await m.answer(t(lang,"welcome").format(name=m.from_user.first_name or "User"),
                   reply_markup=await main_menu_kb(m.from_user.id, lang))

@router.message(Command("setphoto"))
async def cmd_setphoto(m: Message):
    lang = await get_lang(m.from_user.id)
    if not await db.is_admin(m.from_user.id): return await m.answer("⛔")
    if m.reply_to_message and m.reply_to_message.photo:
        await db.set_setting("panel_photo", m.reply_to_message.photo[-1].file_id)
        await m.answer(t(lang,"photo_set"))
    else:
        await m.answer(t(lang,"photo_missing"))

@router.callback_query(F.data == "home")
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_lang(cb.from_user.id)
    try:
        await cb.message.edit_text(t(lang,"welcome").format(name=cb.from_user.first_name or "User"),
                                   reply_markup=await main_menu_kb(cb.from_user.id, lang))
    except Exception:
        await cb.message.answer(t(lang,"welcome").format(name=cb.from_user.first_name or "User"),
                                reply_markup=await main_menu_kb(cb.from_user.id, lang))
    await cb.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    u = await db.get_user(cb.from_user.id)
    txt = t(lang,"profile_title") + "\n\n" + t(lang,"profile_body").format(
        uid=u["user_id"], balance=u["balance"], time=now_str(),
        purchases=u["purchases"], charged=u["total_charged"])
    await cb.message.edit_text(txt, reply_markup=back_kb(lang))
    await cb.answer()

@router.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    await cb.message.edit_text(t(lang,"support").format(ids=await get_support_ids(lang)),
                               reply_markup=back_kb(lang))
    await cb.answer()

@router.callback_query(F.data == "guide")
async def cb_guide(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    rows = []
    if GUIDE_CHANNEL_LINK:
        rows.append([B(t(lang,"open_channel"), url=GUIDE_CHANNEL_LINK, style="success")])
    rows.append([B(t(lang,"back"), cb="home", style="danger")])
    await cb.message.edit_text(t(lang,"guide_msg"), reply_markup=KB(rows))
    await cb.answer()

@router.callback_query(F.data == "report")
async def cb_report(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    rows = []
    if REPORT_CHANNEL_LINK:
        rows.append([B(t(lang,"open_channel"), url=REPORT_CHANNEL_LINK, style="success")])
    rows.append([B(t(lang,"back"), cb="home", style="danger")])
    await cb.message.edit_text(t(lang,"report_msg"), reply_markup=KB(rows))
    await cb.answer()

@router.callback_query(F.data == "lang")
async def cb_lang(cb: CallbackQuery):
    kb = KB([
        [B("🇮🇷 فارسی", cb="setlang:fa", style="success"), B("🇬🇧 English", cb="setlang:en", style="primary")],
        [B("🏠", cb="home", style="danger")],
    ])
    await cb.message.edit_text("🌐 Language / زبان", reply_markup=kb)
    await cb.answer()

@router.callback_query(F.data.startswith("setlang:"))
async def cb_setlang(cb: CallbackQuery):
    lang = cb.data.split(":",1)[1]
    await db.set_lang(cb.from_user.id, lang)
    await cb.answer(t(lang,"lang_set"))
    await cb.message.edit_text(t(lang,"welcome").format(name=cb.from_user.first_name or "User"),
                               reply_markup=await main_menu_kb(cb.from_user.id, lang))

@router.callback_query(F.data == "logout")
async def cb_logout(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    pending_logins.pop(cb.from_user.id, None)
    await db.clear_user_sessions(cb.from_user.id)
    try:
        await cb.message.edit_text(t(lang,"logout_ok"),
                                   reply_markup=await main_menu_kb(cb.from_user.id, lang))
    except Exception:
        await cb.message.answer(t(lang,"logout_ok"))
    await cb.answer()

# ═════ BUY FLOW ═════
@router.callback_query(F.data == "buy")
async def cb_buy(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    await cb.message.edit_text(t(lang,"buy_title"), reply_markup=categories_kb(lang))
    await cb.answer()

@router.callback_query(F.data.startswith("cat:"))
async def cb_cat(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    cat = cb.data.split(":",1)[1]
    panels = await db.panels_by_cat(cat)
    if not panels:
        return await cb.answer(t(lang,"cat_empty"), show_alert=True)
    cd = t(lang,"cat_display")
    await cb.message.edit_text(t(lang,"panel_list").format(cat=cd.get(cat,cat)),
                               reply_markup=await panels_kb(lang, cat))
    await cb.answer()

@router.callback_query(F.data.startswith("panel:"))
async def cb_panel(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    pid = int(cb.data.split(":",1)[1])
    p = await db.get_panel(pid)
    if not p: return await cb.answer(t(lang,"no_accounts"), show_alert=True)
    await cb.message.edit_text(t(lang,"account_list").format(panel=p["name"], price=p["price"]),
                               reply_markup=await accounts_kb(lang, pid))
    await cb.answer()

@router.callback_query(F.data.startswith("cat_of:"))
async def cb_cat_of(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    pid = int(cb.data.split(":",1)[1])
    p = await db.get_panel(pid)
    if not p: return await cb.answer()
    cd = t(lang,"cat_display")
    await cb.message.edit_text(t(lang,"panel_list").format(cat=cd.get(p["category"],p["category"])),
                               reply_markup=await panels_kb(lang, p["category"]))
    await cb.answer()

@router.callback_query(F.data.startswith("acc:"))
async def cb_acc(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    aid = int(cb.data.split(":",1)[1])
    acc = await db.get_account(aid)
    if not acc or acc["status"] != "available":
        return await cb.answer(t(lang,"no_accounts"), show_alert=True)
    p = await db.get_panel(acc["panel_id"])
    if not p: return await cb.answer()
    u = await db.get_user(cb.from_user.id)
    if u["balance"] < p["price"]:
        return await cb.answer(t(lang,"balance_low").format(bal=u["balance"], need=p["price"]), show_alert=True)
    await db.reserve_account(aid, cb.from_user.id)
    card = (await db.get_setting(f"card_{p['created_by']}") or 
            await db.get_setting(f"card_{OWNER_ID}") or "")
    if not card:
        return await cb.answer(t(lang,"no_card"), show_alert=True)
    oid = await db.create_order(cb.from_user.id, aid, p["id"], p["price"])
    await cb.message.edit_text(
        t(lang,"reserved").format(price=p["price"], card=card, minutes=RESERVE_MIN),
        reply_markup=receipt_kb(lang, oid))
    await cb.answer()

@router.callback_query(F.data.startswith("receipt:"))
async def cb_receipt(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":",1)[1])
    await state.update_data(order_id=oid)
    await state.set_state(S.receipt)
    await cb.message.answer(t(lang,"send_receipt"))
    await cb.answer()

@router.message(S.receipt, F.photo)
async def msg_receipt(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    data = await state.get_data()
    oid = data.get("order_id")
    await state.clear()
    if not oid: return await m.answer(t(lang,"invalid"))
    order = await db.get_order(oid)
    if not order or order["user_id"] != m.from_user.id:
        return await m.answer(t(lang,"invalid"))
    fid = m.photo[-1].file_id
    await db.set_order_receipt(oid, fid)
    await db.extend_reservation(order["account_id"], hours=24)
    await m.answer(t(lang,"receipt_sent"))
    panel = await db.get_panel(order["panel_id"])
    acc = await db.get_account(order["account_id"])
    txt = t("fa","order_new").format(
        uid=order["user_id"], panel=panel["name"] if panel else "-",
        phone=acc["phone"] if acc else "-", amount=order["amount"])
    await notify_admins(m.bot, txt, kb=approve_kb(oid), photo=fid)

@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    oid = int(cb.data.split(":",1)[1])
    order = await db.get_order(oid)
    if order and order["user_id"] == cb.from_user.id:
        await db.release_account(order["account_id"])
        await db.reject_order(oid)
    await cb.message.edit_text(t(lang,"invalid"), reply_markup=back_kb(lang,"buy"))
    await cb.answer()

@router.callback_query(F.data.startswith("ap:"))
async def cb_ap(cb: CallbackQuery):
    _, action, oid_s = cb.data.split(":")
    oid = int(oid_s)
    if not await db.is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    order = await db.get_order(oid)
    if not order: return await cb.answer("invalid")
    blang = await get_lang(order["user_id"])
    panel = await db.get_panel(order["panel_id"])
    acc = await db.get_account(order["account_id"])
    if action == "approve":
        if not acc or acc["status"] != "available":
            return await cb.answer("این اکانت دیگه در دسترس نیست", show_alert=True)
        if not await db.deduct_balance(order["user_id"], order["amount"]):
            return await cb.answer("موجودی خریدار کافی نیست", show_alert=True)
        await db.approve_order(oid)
        await db.sell_account(order["account_id"], order["user_id"])
        await db.inc_purchases(order["user_id"])
        try:
            await cb.bot.send_message(
                order["user_id"],
                t(blang,"approved_buyer").format(phone=acc["phone"], twofa=acc["twofa"] or "—"),
                reply_markup=KB([[B(t(blang,"get_code_btn"), cb=f"getcode:{acc['id']}", style="success")]]))
        except Exception as e:
            log.warning(f"buyer notify: {e}")
        
        if REPORT_CHANNEL:
            try:
                me = await cb.bot.get_me()
                btn = B(t("fa","buy_from_channel"), url=f"https://t.me/{me.username}", style="success")
                rep = t("fa","report_text").format(
                    uid=order["user_id"], flag=panel["flag"] if panel else "🌍",
                    panel=panel["name"] if panel else "-",
                    phone=mask_phone(acc["phone"]),
                    amount=order["amount"], date=now_str())
                await cb.bot.send_message(REPORT_CHANNEL, rep, reply_markup=KB([[btn]]))
                log.info("Report sent to channel successfully")
            except Exception as e:
                log.warning(f"report post failed: {e} (Check if bot is admin in {REPORT_CHANNEL})")

        if cb.message.caption is not None:
            await cb.message.edit_caption(caption=cb.message.caption + "\n\n✅ تایید شد")
        else:
            await cb.message.edit_text((cb.message.text or "") + "\n\n✅ تایید شد")
        await cb.answer("✅")
    else:
        await db.reject_order(oid)
        await db.release_account(order["account_id"])
        try:
            await cb.bot.send_message(order["user_id"], t(blang,"rejected_buyer"))
        except Exception: pass
        if cb.message.caption is not None:
            await cb.message.edit_caption(caption=cb.message.caption + "\n\n❌ رد شد")
        else:
            await cb.message.edit_text((cb.message.text or "") + "\n\n❌ رد شد")
        await cb.answer("❌")

@router.callback_query(F.data.startswith("getcode:"))
async def cb_getcode(cb: CallbackQuery):
    lang = await get_lang(cb.from_user.id)
    aid = int(cb.data.split(":",1)[1])
    acc = await db.get_account(aid)
    if not acc or acc["sold_to"] != cb.from_user.id:
        return await cb.answer("⛔", show_alert=True)
    if not acc.get("session"):
        return await cb.answer(t(lang,"get_code_fail"), show_alert=True)
    await cb.answer(t(lang,"get_code_wait"))
    try:
        client = TelegramClient(StringSession(acc["session"]), TG_API_ID, TG_API_HASH)
        await client.connect()
        code = None
        try:
            for m in await client.get_messages(777000, limit=15):
                if m.text:
                    match = re.search(r"\b(\d{5,6})\b", m.text)
                    if match:
                        code = match.group(1); break
        finally:
            try: await client.disconnect()
            except Exception: pass
        if code:
            extra = t(lang,"twofa_line").format(pw=acc["twofa"]) if acc["twofa"] else ""
            await cb.message.answer(t(lang,"get_code_ok").format(code=code, twofa=extra))
        else:
            await cb.message.answer(t(lang,"get_code_fail"))
    except Exception as e:
        log.exception(f"getcode: {e}")
        await cb.message.answer(t(lang,"get_code_fail"))

# ═════ ADD PANEL (admin) ═════
@router.callback_query(F.data == "panel_add")
async def cb_panel_add(cb: CallbackQuery, state: FSMContext):
    if not await db.is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    lang = await get_lang(cb.from_user.id)
    await state.set_state(S.p_name)
    await cb.message.answer(t(lang,"add_panel_name"))
    await cb.answer()

@router.message(S.p_name)
async def msg_p_name(m: Message, state: FSMContext):
    await state.update_data(p_name=m.text.strip())
    await state.set_state(S.p_price)
    lang = await get_lang(m.from_user.id)
    await m.answer(t(lang,"add_panel_price"))

@router.message(S.p_price)
async def msg_p_price(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    try: price = int(m.text.strip().replace(",",""))
    except: return await m.answer(t(lang,"invalid"))
    await state.update_data(p_price=price)
    await state.set_state(S.p_cat)
    await m.answer(t(lang,"add_panel_cat"), reply_markup=categories_kb(lang))

@router.callback_query(S.p_cat, F.data.startswith("cat:"))
async def cb_p_cat(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await state.update_data(p_cat=cb.data.split(":",1)[1])
    await state.set_state(S.p_flag)
    await cb.message.edit_text(t(lang,"add_panel_flag"))
    await cb.answer()

@router.message(S.p_flag)
async def msg_p_flag(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    data = await state.get_data()
    flag = (m.text or "🌍").strip()[:4]
    await db.create_panel(data["p_name"], data["p_price"], data["p_cat"], flag, m.from_user.id)
    await state.clear()
    await m.answer(t(lang,"add_panel_ok"), reply_markup=await main_menu_kb(m.from_user.id, lang))

# ═════ ADD ACCOUNT (admin) ═════
@router.callback_query(F.data == "acc_add")
async def cb_acc_add(cb: CallbackQuery, state: FSMContext):
    if not await db.is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    lang = await get_lang(cb.from_user.id)
    panels = await db.all_panels()
    if not panels:
        return await cb.answer(t(lang,"cat_empty"), show_alert=True)
    rows = [[B(f"{p['flag']} {p['name']}", cb=f"accpanel:{p['id']}", style="primary")] for p in panels]
    rows.append([B(t(lang,"back"), cb="home", style="danger")])
    await state.set_state(S.acc_panel)
    await cb.message.answer(t(lang,"add_acc_choose_panel"), reply_markup=KB(rows))
    await cb.answer()

@router.callback_query(S.acc_panel, F.data.startswith("accpanel:"))
async def cb_acc_panel(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    await state.update_data(panel_id=int(cb.data.split(":",1)[1]))
    await state.set_state(S.acc_phone)
    await cb.message.edit_text(t(lang,"add_acc_phone"))
    await cb.answer()

@router.message(S.acc_phone)
async def msg_acc_phone(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    phone = m.text.strip()
    if not phone.startswith("+") or len(phone) < 8:
        return await m.answer(t(lang,"invalid"))
    try:
        client = TelegramClient(StringSession(), TG_API_ID, TG_API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        pending_logins[m.from_user.id] = {
            "client": client, "phone": phone, "hash": sent.phone_code_hash}
        await state.set_state(S.acc_code)
        await m.answer(t(lang,"add_acc_code"))
    except Exception as e:
        log.exception("send_code")
        await m.answer(t(lang,"add_acc_err").format(err=str(e)[:150]))

@router.message(S.acc_code)
async def msg_acc_code(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    p = pending_logins.get(m.from_user.id)
    if not p: return await m.answer(t(lang,"invalid"))
    try:
        await p["client"].sign_in(phone=p["phone"], code=m.text.strip(), phone_code_hash=p["hash"])
    except SessionPasswordNeededError:
        await state.set_state(S.acc_2fa)
        return await m.answer(t(lang,"add_acc_2fa"))
    except Exception as e:
        return await m.answer(t(lang,"add_acc_err").format(err=str(e)[:150]))
    await _save_acc(m, state, p, "")

@router.message(S.acc_2fa)
async def msg_acc_2fa(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    p = pending_logins.get(m.from_user.id)
    if not p: return await m.answer(t(lang,"invalid"))
    pw = m.text.strip()
    try:
        await p["client"].sign_in(password=pw)
    except Exception as e:
        return await m.answer(t(lang,"add_acc_err").format(err=str(e)[:150]))
    await _save_acc(m, state, p, pw)

async def _save_acc(m: Message, state: FSMContext, pending: dict, twofa: str):
    lang = await get_lang(m.from_user.id)
    data = await state.get_data()
    session_str = pending["client"].session.save()
    await db.add_account(data["panel_id"], pending["phone"], session_str, twofa)
    try: await pending["client"].disconnect()
    except: pass
    pending_logins.pop(m.from_user.id, None)
    await state.clear()
    await m.answer(t(lang,"add_acc_ok"), reply_markup=await main_menu_kb(m.from_user.id, lang))

# ═════ ADD ADMIN (owner) ═════
@router.callback_query(F.data == "admin_add")
async def cb_admin_add(cb: CallbackQuery, state: FSMContext):
    lang = await get_lang(cb.from_user.id)
    if cb.from_user.id != OWNER_ID:
        return await cb.answer(t(lang,"add_admin_fail"), show_alert=True)
    await state.set_state(S.a_id)
    await cb.message.answer(t(lang,"add_admin_id"))
    await cb.answer()

@router.message(S.a_id)
async def msg_admin_id(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    try: uid = int(m.text.strip())
    except: return await m.answer(t(lang,"invalid"))
    await db.add_admin(uid, "", m.from_user.id)
    await state.clear()
    await m.answer(t(lang,"add_admin_ok"), reply_markup=await main_menu_kb(m.from_user.id, lang))

# ═════ SET CARD ═════
@router.callback_query(F.data == "set_card")
async def cb_set_card(cb: CallbackQuery, state: FSMContext):
    if not await db.is_admin(cb.from_user.id):
        return await cb.answer("⛔", show_alert=True)
    lang = await get_lang(cb.from_user.id)
    await state.set_state(S.card)
    await cb.message.answer(t(lang,"card_prompt"))
    await cb.answer()

@router.message(S.card)
async def msg_card(m: Message, state: FSMContext):
    lang = await get_lang(m.from_user.id)
    await db.set_setting(f"card_{m.from_user.id}", m.text.strip())
    await state.clear()
    await m.answer(t(lang,"card_ok"), reply_markup=await main_menu_kb(m.from_user.id, lang))

# ═════ STARTUP ═════
async def resolve_default_admins(bot: Bot):
    global OWNER_USERNAME
    if not DEFAULT_ADMINS: return
    for entry in [e.strip() for e in DEFAULT_ADMINS.split(",") if e.strip()]:
        try:
            if entry.startswith("@"):
                chat = await bot.get_chat(entry)
                await db.add_admin(chat.id, entry, OWNER_ID)
                log.info(f"Admin added: {entry} → {chat.id}")
            else:
                parts = entry.split(":", 1)
                uid = int(parts[0])
                uname = parts[1] if len(parts) > 1 else ""
                await db.add_admin(uid, uname, OWNER_ID)
                log.info(f"Admin added: {uid}")
        except Exception as e:
            log.warning(f"Could not add default admin {entry}: {e}")

async def main():
    if not BOT_TOKEN: raise SystemExit("BOT_TOKEN missing")
    if not OWNER_ID: raise SystemExit("OWNER_ID missing")
    await db.init()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    me = await bot.get_me()
    log.info(f"Bot started: @{me.username}")
    global OWNER_USERNAME
    if not OWNER_USERNAME:
        try:
            oc = await bot.get_chat(OWNER_ID)
            if oc.username: OWNER_USERNAME = f"@{oc.username}"
        except: pass
    await resolve_default_admins(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): log.info("stopped")
