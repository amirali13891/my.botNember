# -*- coding: utf-8 -*-
"""
Virtual Number Sales Bot — Final (Hardcoded Support, No Bugs)
"""
import asyncio, logging, os, re
from datetime import datetime, timezone
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

# 🔴 آیدی‌های شما مستقیماً اینجا تنظیم شدند
OWNER_ID = 8264228802
OWNER_USERNAME = "@gahtl"

ADMIN_ID = 7260131929
ADMIN_USERNAME = "@kakashi_n1"

TG_API_ID = int(os.getenv("TG_API_ID", "0") or 0)
TG_API_HASH = os.getenv("TG_API_HASH", "").strip()
MAIN_CHANNEL_LINK = os.getenv("MAIN_CHANNEL_LINK", "").strip()
REPORT_CHANNEL_LINK = os.getenv("REPORT_CHANNEL_LINK", "").strip()
GUIDE_CHANNEL_LINK = os.getenv("GUIDE_CHANNEL_LINK", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot.db")

CARD_NUMBER = "6219861885186253"
CARD_HOLDER = "هوشیار"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("vbot")
router = Router()

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
        "support": "🎧 <b>پشتیبانی</b>\n\nبرای ارتباط با پشتیبانی به آیدی‌های زیر پیام دهید:\n\n👑 مالک:\n{owner}\n\n👤 ادمین:\n{admin}\n\nممنون که با ما هستید 🌹",
        "buy_title": "🛒 <b>خرید شماره مجازی</b>\nلطفاً یک دسته‌بندی انتخاب کنید:",
        "cat_empty": "❌ در این دسته فعلاً پنلی ثبت نشده.",
        "panel_list": "📦 پنل‌های موجود در دسته <b>{cat}</b>:",
        "no_accounts": "😔 در این پنل موجودی نیست.",
        "balance_low": "❌ موجودی کافی نیست.\n💰 موجودی: <b>{bal:,}</b> تومان\n💵 نیاز: <b>{need:,}</b> تومان\n\nجهت شارژ به بخش شارژ حساب مراجعه کنید.",
        "buy_success": "🎉 خرید موفق!\n\n📱 شماره: <code>{phone}</code>\n🔐 رمز دو مرحله‌ای: <code>{twofa}</code>\n\nبرای دریافت کد ورود، دکمه «دریافت کد» را بزنید.",
        "get_code_btn": "🔑 دریافت کد",
        "get_code_wait": "⏳ در حال دریافت کد از تلگرام...",
        "get_code_ok": "🔑 کد ورود شما: <code>{code}</code>{twofa}",
        "get_code_fail": "⚠️ کدی یافت نشد. ابتدا در اپ تلگرام شماره را وارد کنید تا کد ارسال شود، سپس دوباره تلاش کنید.",
        "twofa_line": "\n🔐 رمز دو مرحله‌ای: <code>{pw}</code>",
        
        "charge_amount": "💰 لطفاً مبلغ مورد نظر (به تومان) را فقط به صورت عدد وارد کنید (بدون کاما و نقطه):",
        "charge_card": ("💳 <b>درخواست شارژ حساب</b>\n\n"
                        "مبلغ قابل پرداخت (کلیک کنید تا کپی شود):\n<code>{amount}</code> تومان\n\n"
                        "لطفاً مبلغ فوق را به شماره کارت زیر واریز کنید:\n"
                        "<b>به نام: {holder}</b>\n"
                        "شماره کارت (کلیک کنید تا کپی شود):\n<code>{card}</code>\n\n"
                        "سپس <b>عکس رسید</b> را ارسال کنید.\n\n"
                        "📌 <b>نکته مهم:</b> برای اینکه بتونیم حساب شما رو شارژ کنیم، لطفاً همراه با رسید، <b>آیدی عددی خودتون</b> رو هم ارسال کنید.\n"
                        "اگر آیدی عددی خودتون رو نمی‌دونید، ربات @TGDNAbot رو استارت کنید."),
        "charge_receipt_sent": "✅ رسید شما برای بررسی به مالک ارسال شد.\nلطفاً منتظر تایید بمانید.",
        "charge_new_admin": "💳 <b>درخواست شارژ جدید</b>\n\nآیدی کاربر: <code>{uid}</code>\nیوزرنیم: {username}\nمبلغ: <b>{amount:,}</b> تومان",
        "charge_approved_user": "🎉 حساب شما با موفقیت شارژ شد!\n\nمبلغ: <b>{amount:,}</b> تومان\n💰 موجودی فعلی شما: <b>{balance:,}</b> تومان\n\nممنون از صبوری شما 🌹",
        
        "add_panel_name": "🏷 نام پنل را وارد کنید:",
        "add_panel_price": "💰 قیمت (تومان) را وارد کنید:",
        "add_panel_cat": "📂 دسته‌بندی را انتخاب کنید:",
        "add_panel_flag": "🌍 فلگ کشور را وارد کنید (مثلاً 🇺🇸):",
        "add_panel_ok": "✅ پنل ایجاد شد.",
        
        "add_acc_choose_panel": "➕ <b>افزودن شماره</b>\nیک پنل انتخاب کنید:",
        "add_acc_phone": "📱 شماره را با فرمت بین‌المللی ارسال کنید (مثلاً +989121234567):",
        "add_acc_code": "📨 کد ارسال شده را وارد کنید:",
        "add_acc_2fa": "🔐 رمز دو مرحله‌ای را وارد کنید:",
        "add_acc_ok": "✅ اکانت با موفقیت اضافه شد!",
        "add_acc_err": "❌ خطا در افزودن اکانت:\n<code>{err}</code>",
        
        "inc_balance_prompt": "👤 آیدی عددی کاربری که می‌خواهید موجودیش را افزایش دهید را وارد کنید:",
        "inc_balance_amount": "💰 مبلغی که می‌خواهید به موجودی این کاربر اضافه کنید را وارد کنید:",
        "inc_balance_ok": "✅ موجودی کاربر با موفقیت افزایش یافت.",
        
        "btn_profile": "👤 حساب کاربری", "btn_support": "🎧 پشتیبانی",
        "btn_buy": "🛒 خرید شماره", "btn_guide": "📚 توضیحات",
        "btn_stock": "📦 لیست موجودی", "btn_charge": "💳 شارژ حساب",
        "btn_main_channel": "🏪 چنل اصلی", "btn_report_channel": "📣 چنل گزارشات",
        "btn_add_account": "➕ افزودن شماره", "btn_add_panel": "📦 افزودن پنل",
        "btn_inc_balance": "💰 افزایش موجودی",
        "btn_back": "◀️ بازگشت", "btn_home": "🏠 منوی اصلی",
        
        "guide_msg": "📚 برای مشاهده آموزش‌ها روی دکمه زیر بزنید:",
        "open_channel": "🔗 ورود به کانال",
        "invalid": "❌ مقدار نامعتبر.",
        "cat_display": {"scam": "🚫 اسکم", "fake": "🎭 جعلی", "ready": "✅ نوریپ", "rep": "♻️ ریپ دایم"},
    }
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
            CREATE TABLE IF NOT EXISTS panels(
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                price INTEGER NOT NULL, category TEXT NOT NULL,
                flag TEXT DEFAULT '🌍', created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT, panel_id INTEGER NOT NULL,
                phone TEXT, session TEXT, twofa TEXT, status TEXT DEFAULT 'available',
                sold_to INTEGER, created_at TEXT
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

    async def add_balance(self, uid: int, amount: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET balance=balance+?, total_charged=total_charged+? WHERE user_id=?",
                             (amount, amount, uid))
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

    async def create_panel(self, name, price, category, flag) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("INSERT INTO panels(name, price, category, flag, created_at) VALUES(?,?,?,?,?)",
                (name, price, category, flag, datetime.now(timezone.utc).isoformat()))
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

    async def add_account(self, pid, phone, session, twofa=""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO accounts(panel_id, phone, session, twofa, status, created_at) VALUES(?,?,?,?,'available',?)",
                (pid, phone, session, twofa, datetime.now(timezone.utc).isoformat()))
            await db.commit()

    async def get_available_account(self, panel_id) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM accounts WHERE panel_id=? AND status='available' LIMIT 1", (panel_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def sell_account(self, aid, uid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE accounts SET status='sold', sold_to=? WHERE id=?", (uid, aid))
            await db.execute("UPDATE users SET purchases=purchases+1 WHERE user_id=?", (uid,))
            await db.commit()

    async def get_account(self, aid) -> Optional[dict]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM accounts WHERE id=?", (aid,))
            row = await cur.fetchone()
            return dict(row) if row else None

db = DB(DB_PATH)

# ════════════════ BUTTONS ════════════════
def B(text: str, cb: Optional[str] = None, url: Optional[str] = None) -> InlineKeyboardButton:
    kw = {"text": text}
    if cb is not None: kw["callback_data"] = cb
    if url is not None: kw["url"] = url
    return InlineKeyboardButton(**kw)

def KB(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ════════════════ STATES ════════════════
class S(StatesGroup):
    acc_panel = State(); acc_phone = State(); acc_code = State(); acc_2fa = State()
    p_name = State(); p_price = State(); p_cat = State(); p_flag = State()
    charge_amount = State(); charge_receipt = State()
    inc_uid = State(); inc_amount = State()

# ════════════════ KEYBOARDS ════════════════
async def main_menu_kb(uid: int):
    is_admin = (uid == OWNER_ID or uid == ADMIN_ID)
    rows = [
        [B(t("fa","btn_profile"), cb="profile"), B(t("fa","btn_support"), cb="support")],
        [B(t("fa","btn_buy"), cb="buy")],
        [B(t("fa","btn_stock"), cb="stock"), B(t("fa","btn_charge"), cb="charge")],
    ]
    row_ch = []
    if MAIN_CHANNEL_LINK:
        row_ch.append(B(t("fa","btn_main_channel"), url=MAIN_CHANNEL_LINK))
    if REPORT_CHANNEL_LINK:
        row_ch.append(B(t("fa","btn_report_channel"), url=REPORT_CHANNEL_LINK))
    if row_ch:
        rows.append(row_ch)
        
    rows.append([B(t("fa","btn_guide"), cb="guide")])
    
    if is_admin:
        rows.append([B(t("fa","btn_add_account"), cb="acc_add"), B(t("fa","btn_add_panel"), cb="panel_add")])
        if uid == OWNER_ID:
            rows.append([B(t("fa","btn_inc_balance"), cb="inc_balance")])
    return KB(rows)

def back_kb(cb="home"):
    return KB([[B(t("fa","btn_back"), cb=cb)]])

def categories_kb(prefix="cat"):
    cd = t("fa","cat_display")
    return KB([
        [B(cd["scam"], cb=f"{prefix}:scam")],
        [B(cd["fake"], cb=f"{prefix}:fake")],
        [B(cd["ready"], cb=f"{prefix}:ready")],
        [B(cd["rep"], cb=f"{prefix}:rep")],
        [B(t("fa","btn_back"), cb="home")],
    ])

async def panels_kb(category):
    panels = await db.panels_by_cat(category)
    rows = [[B(f"{p['flag']} {p['name']} — {p['price']:,} تومان", cb=f"panel:{p['id']}")] for p in panels]
    rows.append([B(t("fa","btn_back"), cb="stock")])
    return KB(rows)

# ════════════════ HANDLERS ════════════════
@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    await db.get_user(m.from_user.id)
    text = t("fa","welcome").format(name=m.from_user.first_name or "User")
    await m.answer(text, reply_markup=await main_menu_kb(m.from_user.id))

@router.callback_query(F.data == "home")
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cb.message.edit_text(t("fa","welcome").format(name=cb.from_user.first_name or "User"),
                                   reply_markup=await main_menu_kb(cb.from_user.id))
    except Exception:
        pass
    await cb.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    u = await db.get_user(cb.from_user.id)
    txt = t("fa","profile_title") + "\n\n" + t("fa","profile_body").format(
        uid=u["user_id"], balance=u["balance"], time=datetime.now().strftime("%H:%M"),
        purchases=u["purchases"], charged=u["total_charged"])
    await cb.message.edit_text(txt, reply_markup=back_kb())
    await cb.answer()

@router.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    owner_disp = f"{OWNER_USERNAME} (ID: {OWNER_ID})"
    admin_disp = f"{ADMIN_USERNAME} (ID: {ADMIN_ID})"
    txt = t("fa","support").format(owner=owner_disp, admin=admin_disp)
    await cb.message.edit_text(txt, reply_markup=back_kb())
    await cb.answer()

@router.callback_query(F.data == "guide")
async def cb_guide(cb: CallbackQuery):
    rows = []
    if GUIDE_CHANNEL_LINK:
        rows.append([B(t("fa","open_channel"), url=GUIDE_CHANNEL_LINK)])
    rows.append([B(t("fa","btn_back"), cb="home")])
    await cb.message.edit_text(t("fa","guide_msg"), reply_markup=KB(rows))
    await cb.answer()

# ═════ لیست موجودی و خرید ═════
@router.callback_query(F.data == "stock")
async def cb_stock(cb: CallbackQuery):
    await cb.message.edit_text(t("fa","buy_title"), reply_markup=categories_kb("scat"))
    await cb.answer()

@router.callback_query(F.data == "buy")
async def cb_buy(cb: CallbackQuery):
    await cb.message.edit_text(t("fa","buy_title"), reply_markup=categories_kb("bcat"))
    await cb.answer()

@router.callback_query(F.data.startswith("scat:"))
async def cb_scat(cb: CallbackQuery):
    cat = cb.data.split(":",1)[1]
    panels = await db.panels_by_cat(cat)
    if not panels:
        return await cb.answer(t("fa","cat_empty"), show_alert=True)
    cd = t("fa","cat_display")
    await cb.message.edit_text(t("fa","panel_list").format(cat=cd.get(cat,cat)),
                               reply_markup=await panels_kb(cat))
    await cb.answer()

@router.callback_query(F.data.startswith("bcat:"))
async def cb_bcat(cb: CallbackQuery):
    cat = cb.data.split(":",1)[1]
    panels = await db.panels_by_cat(cat)
    if not panels:
        return await cb.answer(t("fa","cat_empty"), show_alert=True)
    cd = t("fa","cat_display")
    await cb.message.edit_text(t("fa","panel_list").format(cat=cd.get(cat,cat)),
                               reply_markup=await panels_kb(cat))
    await cb.answer()

@router.callback_query(F.data.startswith("panel:"))
async def cb_panel(cb: CallbackQuery):
    pid = int(cb.data.split(":",1)[1])
    p = await db.get_panel(pid)
    if not p: return await cb.answer("پنل یافت نشد.", show_alert=True)
    
    acc = await db.get_available_account(pid)
    if not acc:
        return await cb.answer(t("fa","no_accounts"), show_alert=True)
        
    u = await db.get_user(cb.from_user.id)
    if u["balance"] < p["price"]:
        return await cb.answer(t("fa","balance_low").format(bal=u["balance"], need=p["price"]), show_alert=True)
        
    await db.deduct_balance(cb.from_user.id, p["price"])
    await db.sell_account(acc["id"], cb.from_user.id)
    
    txt = t("fa","buy_success").format(phone=acc["phone"], twofa=acc["twofa"] or "ندارد")
    kb = KB([[B(t("fa","get_code_btn"), cb=f"getcode:{acc['id']}")], [B(t("fa","btn_home"), cb="home")]])
    await cb.message.edit_text(txt, reply_markup=kb)
    await cb.answer("✅ خرید موفقیت‌آمیز بود.")

@router.callback_query(F.data.startswith("getcode:"))
async def cb_getcode(cb: CallbackQuery):
    aid = int(cb.data.split(":",1)[1])
    acc = await db.get_account(aid)
    if not acc or acc["sold_to"] != cb.from_user.id:
        return await cb.answer("⛔", show_alert=True)
    if not acc.get("session"):
        return await cb.answer(t("fa","get_code_fail"), show_alert=True)
    await cb.answer(t("fa","get_code_wait"))
    try:
        client = TelegramClient(StringSession(acc["session"]), TG_API_ID, TG_API_HASH)
        await client.connect()
        code = None
        for m in await client.get_messages(777000, limit=15):
            if m.text:
                match = re.search(r"\b(\d{5,6})\b", m.text)
                if match:
                    code = match.group(1); break
        await client.disconnect()
        if code:
            extra = t("fa","twofa_line").format(pw=acc["twofa"]) if acc["twofa"] else ""
            await cb.message.answer(t("fa","get_code_ok").format(code=code, twofa=extra))
        else:
            await cb.message.answer(t("fa","get_code_fail"))
    except Exception as e:
        log.exception(f"getcode: {e}")
        await cb.message.answer(t("fa","get_code_fail"))

# ═════ شارژ حساب ═════
@router.callback_query(F.data == "charge")
async def cb_charge(cb: CallbackQuery, state: FSMContext):
    await state.set_state(S.charge_amount)
    await cb.message.edit_text(t("fa","charge_amount"), reply_markup=back_kb())
    await cb.answer()

@router.message(S.charge_amount)
async def msg_charge_amount(m: Message, state: FSMContext):
    try:
        amount = int(m.text.strip().replace(",","").replace(".",""))
        if amount < 1000: raise ValueError
    except:
        return await m.answer(t("fa","invalid"))
    
    await state.update_data(charge_amount=amount)
    await state.set_state(S.charge_receipt)
    
    await m.answer(t("fa","charge_card").format(amount=amount, card=CARD_NUMBER, holder=CARD_HOLDER))

@router.message(S.charge_receipt, F.photo)
async def msg_charge_receipt(m: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("charge_amount")
    await state.clear()
    
    await m.answer(t("fa","charge_receipt_sent"))
    
    username = f"@{m.from_user.username}" if m.from_user.username else "ندارد"
    txt = t("fa","charge_new_admin").format(uid=m.from_user.id, username=username, amount=amount)
    kb = KB([[B("✅ تایید شارژ", cb=f"apcharge:{m.from_user.id}:{amount}")]])
    
    try:
        await m.bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=txt, reply_markup=kb)
    except Exception as e:
        log.warning(f"Could not send charge receipt to owner: {e}")

@router.callback_query(F.data.startswith("apcharge:"))
async def cb_apcharge(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID:
        return await cb.answer("⛔", show_alert=True)
    _, uid_s, amt_s = cb.data.split(":")
    uid, amount = int(uid_s), int(amt_s)
    
    await db.add_balance(uid, amount)
    u = await db.get_user(uid)
    
    try:
        await cb.bot.send_message(uid, t("fa","charge_approved_user").format(amount=amount, balance=u["balance"]))
    except: pass
    
    await cb.message.edit_caption(caption=(cb.message.caption or "") + "\n\n✅ تایید شد")
    await cb.answer("✅")

# ═════ افزایش موجودی توسط مالک ═════
@router.callback_query(F.data == "inc_balance")
async def cb_inc_balance(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != OWNER_ID: return await cb.answer("⛔")
    await state.set_state(S.inc_uid)
    await cb.message.answer(t("fa","inc_balance_prompt"))
    await cb.answer()

@router.message(S.inc_uid)
async def msg_inc_uid(m: Message, state: FSMContext):
    try: uid = int(m.text.strip())
    except: return await m.answer(t("fa","invalid"))
    await state.update_data(inc_uid=uid)
    await state.set_state(S.inc_amount)
    await m.answer(t("fa","inc_balance_amount"))

@router.message(S.inc_amount)
async def msg_inc_amount(m: Message, state: FSMContext):
    try: amount = int(m.text.strip().replace(",",""))
    except: return await m.answer(t("fa","invalid"))
    data = await state.get_data()
    uid = data.get("inc_uid")
    
    await db.add_balance(uid, amount)
    u = await db.get_user(uid)
    
    try:
        await m.bot.send_message(uid, t("fa","charge_approved_user").format(amount=amount, balance=u["balance"]))
    except: pass
    
    await state.clear()
    await m.answer(t("fa","inc_balance_ok"), reply_markup=await main_menu_kb(m.from_user.id))

# ═════ پنل ادمین: افزودن پنل ═════
@router.callback_query(F.data == "panel_add")
async def cb_panel_add(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in (OWNER_ID, ADMIN_ID): return await cb.answer("⛔")
    await state.set_state(S.p_name)
    await cb.message.answer(t("fa","add_panel_name"))
    await cb.answer()

@router.message(S.p_name)
async def msg_p_name(m: Message, state: FSMContext):
    await state.update_data(p_name=m.text.strip())
    await state.set_state(S.p_price)
    await m.answer(t("fa","add_panel_price"))

@router.message(S.p_price)
async def msg_p_price(m: Message, state: FSMContext):
    try: price = int(m.text.strip().replace(",",""))
    except: return await m.answer(t("fa","invalid"))
    await state.update_data(p_price=price)
    await state.set_state(S.p_cat)
    await m.answer(t("fa","add_panel_cat"), reply_markup=categories_kb("pcat"))

@router.callback_query(S.p_cat, F.data.startswith("pcat:"))
async def cb_p_cat(cb: CallbackQuery, state: FSMContext):
    await state.update_data(p_cat=cb.data.split(":",1)[1])
    await state.set_state(S.p_flag)
    await cb.message.edit_text(t("fa","add_panel_flag"))
    await cb.answer()

@router.message(S.p_flag)
async def msg_p_flag(m: Message, state: FSMContext):
    data = await state.get_data()
    flag = (m.text or "🌍").strip()[:4]
    await db.create_panel(data["p_name"], data["p_price"], data["p_cat"], flag)
    await state.clear()
    await m.answer(t("fa","add_panel_ok"), reply_markup=await main_menu_kb(m.from_user.id))

# ═════ پنل ادمین: افزودن شماره ═════
@router.callback_query(F.data == "acc_add")
async def cb_acc_add(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in (OWNER_ID, ADMIN_ID): return await cb.answer("⛔")
    panels = await db.all_panels()
    if not panels: return await cb.answer(t("fa","cat_empty"), show_alert=True)
    rows = [[B(f"{p['flag']} {p['name']}", cb=f"accpanel:{p['id']}")] for p in panels]
    rows.append([B(t("fa","btn_back"), cb="home")])
    await state.set_state(S.acc_panel)
    await cb.message.answer(t("fa","add_acc_choose_panel"), reply_markup=KB(rows))
    await cb.answer()

@router.callback_query(S.acc_panel, F.data.startswith("accpanel:"))
async def cb_acc_panel(cb: CallbackQuery, state: FSMContext):
    await state.update_data(panel_id=int(cb.data.split(":",1)[1]))
    await state.set_state(S.acc_phone)
    await cb.message.edit_text(t("fa","add_acc_phone"))
    await cb.answer()

@router.message(S.acc_phone)
async def msg_acc_phone(m: Message, state: FSMContext):
    phone = m.text.strip()
    if not phone.startswith("+") or len(phone) < 8:
        return await m.answer(t("fa","invalid"))
    try:
        client = TelegramClient(StringSession(), TG_API_ID, TG_API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        globals()[f"pending_{m.from_user.id}"] = {"client": client, "phone": phone, "hash": sent.phone_code_hash}
        await state.set_state(S.acc_code)
        await m.answer(t("fa","add_acc_code"))
    except Exception as e:
        await m.answer(t("fa","add_acc_err").format(err=str(e)[:150]))

@router.message(S.acc_code)
async def msg_acc_code(m: Message, state: FSMContext):
    p = globals().get(f"pending_{m.from_user.id}")
    if not p: return await m.answer(t("fa","invalid"))
    try:
        await p["client"].sign_in(phone=p["phone"], code=m.text.strip(), phone_code_hash=p["hash"])
    except SessionPasswordNeededError:
        await state.set_state(S.acc_2fa)
        return await m.answer(t("fa","add_acc_2fa"))
    except Exception as e:
        return await m.answer(t("fa","add_acc_err").format(err=str(e)[:150]))
    await _save_acc(m, state, p, "")

@router.message(S.acc_2fa)
async def msg_acc_2fa(m: Message, state: FSMContext):
    p = globals().get(f"pending_{m.from_user.id}")
    if not p: return await m.answer(t("fa","invalid"))
    pw = m.text.strip()
    try:
        await p["client"].sign_in(password=pw)
    except Exception as e:
        return await m.answer(t("fa","add_acc_err").format(err=str(e)[:150]))
    await _save_acc(m, state, p, pw)

async def _save_acc(m: Message, state: FSMContext, pending: dict, twofa: str):
    data = await state.get_data()
    session_str = pending["client"].session.save()
    await db.add_account(data["panel_id"], pending["phone"], session_str, twofa)
    try: await pending["client"].disconnect()
    except: pass
    globals().pop(f"pending_{m.from_user.id}", None)
    await state.clear()
    await m.answer(t("fa","add_acc_ok"), reply_markup=await main_menu_kb(m.from_user.id))

# ═════ STARTUP ═════
async def main():
    if not BOT_TOKEN: raise SystemExit("BOT_TOKEN missing")
    await db.init()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    log.info(f"Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): log.info("stopped")
