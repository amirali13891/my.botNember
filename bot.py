# -*- coding: utf-8 -*-
import asyncio, logging, os, re
from datetime import datetime, timezone
from typing import Optional
import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

BOT_TOKEN = "9002271720:AAHFjTnbfv0gQHGgTXtLlRilkx0LEMHL8SE"
OWNER_ID = 8264228802
OWNER_USERNAME = "@gahtl"
ADMIN_ID = 7260131929
ADMIN_USERNAME = "@kakashi_n1"
TG_API_ID = 20550014
TG_API_HASH = "64144b6ae3b184ebde03062fbdc1a6c7"
MAIN_CHANNEL_LINK = "https://t.me/SHOP_Number_KhaN"
REPORT_CHANNEL_LINK = "https://t.me/Purchasereportskhan"
REPORT_CHANNEL_ID = "-1004383972134"
GUIDE_CHANNEL_LINK = "https://t.me/+AYb_FLKESTpkZDE0"
DB_PATH = os.getenv("DB_PATH", "bot.db")
FORCE_JOIN_1 = "@Group_SHOP_KhaN"
FORCE_JOIN_2 = "@SHOP_Number_KhaN"
CARD_NUMBER = "6219861885186253"
CARD_HOLDER = "هوشیار"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vbot")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()

class DB:
    def __init__(self, path): self.path = path
    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
            CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, total_charged INTEGER DEFAULT 0, purchases INTEGER DEFAULT 0, created_at TEXT);
            CREATE TABLE IF NOT EXISTS panels(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, category TEXT, flag TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY AUTOINCREMENT, panel_id INTEGER, phone TEXT, session TEXT, twofa TEXT, status TEXT DEFAULT 'available', sold_to INTEGER, created_at TEXT);
            """)
            await db.commit()
    async def get_user(self, uid):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row:
                await db.execute("INSERT INTO users(user_id, created_at) VALUES(?,?)", (uid, datetime.now(timezone.utc).isoformat()))
                await db.commit()
                cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
                row = await cur.fetchone()
            return dict(row)
    async def add_bal(self, uid, amt):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET balance=balance+?, total_charged=total_charged+? WHERE user_id=?", (amt, amt, uid))
            await db.commit()
    async def sub_bal(self, uid, amt):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
            row = await cur.fetchone()
            if not row or row["balance"] < amt: return False
            await db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (amt, uid))
            await db.commit()
            return True
    async def create_panel(self, name, price, cat, flag):
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("INSERT INTO panels(name, price, category, flag, created_at) VALUES(?,?,?,?,?)", (name, price, cat, flag, datetime.now(timezone.utc).isoformat()))
            await db.commit(); return cur.lastrowid
    async def get_panels(self, cat):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM panels WHERE category=? ORDER BY id DESC", (cat,))
            return [dict(r) for r in await cur.fetchall()]
    async def all_panels(self):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM panels ORDER BY id DESC")
            return [dict(r) for r in await cur.fetchall()]
    async def get_panel(self, pid):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM panels WHERE id=?", (pid,))
            row = await cur.fetchone(); return dict(row) if row else None
    async def add_acc(self, pid, phone, sess, twofa=""):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO accounts(panel_id, phone, session, twofa, created_at) VALUES(?,?,?,?,?)", (pid, phone, sess, twofa, datetime.now(timezone.utc).isoformat()))
            await db.commit()
    async def get_avail_acc(self, pid):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM accounts WHERE panel_id=? AND status='available' LIMIT 1", (pid,))
            row = await cur.fetchone(); return dict(row) if row else None
    async def sell_acc(self, aid, uid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE accounts SET status='sold', sold_to=? WHERE id=?", (uid, aid))
            await db.execute("UPDATE users SET purchases=purchases+1 WHERE user_id=?", (uid,))
            await db.commit()
    async def get_acc(self, aid):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM accounts WHERE id=?", (aid,))
            row = await cur.fetchone(); return dict(row) if row else None
    async def clear_sess(self, aid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE accounts SET session=NULL WHERE id=?", (aid,))
            await db.commit()
    async def del_panel(self, pid):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("DELETE FROM panels WHERE id=?", (pid,))
            await db.execute("DELETE FROM accounts WHERE panel_id=? AND status='available'", (pid,))
            await db.commit()

db = DB(DB_PATH)

def B(text, cb=None, url=None):
    kw = {"text": text}
    if cb: kw["callback_data"] = cb
    if url: kw["url"] = url
    return InlineKeyboardButton(**kw)

def KB(rows): return InlineKeyboardMarkup(inline_keyboard=rows)

class S(StatesGroup):
    acc_panel, acc_phone, acc_code, acc_2fa = State(), State(), State(), State()
    p_name, p_price, p_cat, p_flag = State(), State(), State(), State()
    charge_amount, charge_receipt = State(), State()
    inc_uid, inc_amount = State(), State()

def mask_p(p): return p[:3] + "***" + p[-3:] if len(p) > 6 else p
def mask_u(uid): return str(uid)[:-3] + "***" if len(str(uid)) > 3 else "***"

async def check_join(uid):
    try:
        m1 = await bot.get_chat_member(FORCE_JOIN_1, uid)
        m2 = await bot.get_chat_member(FORCE_JOIN_2, uid)
        return m1.status in ["member", "administrator", "creator"] and m2.status in ["member", "administrator", "creator"]
    except: return False

async def join_prompt(m):
    kb = KB([[B("📢 کانال شاپ", url=f"https://t.me/{FORCE_JOIN_1.lstrip('@')}")], [B("📢 کانال شماره", url=f"https://t.me/{FORCE_JOIN_2.lstrip('@')}")], [B("✅ عضو شدم", cb="check_join")]])
    await m.answer("⚠️ <b>کاربر گرامی</b>\nبرای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:\n\nسپس دکمه «✅ عضو شدم» را بزنید.", reply_markup=kb)

async def main_kb(uid):
    is_admin = uid in (OWNER_ID, ADMIN_ID)
    rows = [
        [B("👤 حساب کاربری", "profile"), B("🎧 پشتیبانی", "support")],
        [B("🛒 خرید شماره", "buy")],
        [B("📦 لیست موجودی", "stock"), B("💳 شارژ حساب", "charge")],
        [B("🏪 چنل اصلی", url=MAIN_CHANNEL_LINK), B("📣 چنل گزارشات", url=REPORT_CHANNEL_LINK)],
        [B("📚 توضیحات", "guide")]
    ]
    if is_admin:
        rows.append([B("➕ افزودن شماره", "acc_add"), B("📦 افزودن پنل", "panel_add")])
        if uid == OWNER_ID:
            rows.append([B("🗑 حذف پنل", "panel_del")])
            rows.append([B("💰 افزایش موجودی", "inc_balance")])
    return KB(rows)

def back_kb(cb="home"): return KB([[B("◀️ بازگشت", cb=cb)]])

def cats_kb(prefix):
    return KB([[B("🚫 اسکم", f"{prefix}:scam")], [B("🎭 جعلی", f"{prefix}:fake")], [B("✅ نوریپ", f"{prefix}:ready")], [B("♻️ ریپ دایم", f"{prefix}:rep")], [B("◀️ بازگشت", "home")]])

async def panels_kb(cat):
    panels = await db.get_panels(cat)
    rows = [[B(f"{p['flag']} {p['name']} — {p['price']:,} ت", f"panel:{p['id']}")] for p in panels]
    rows.append([B("◀️ بازگشت", "stock")])
    return KB(rows)

@router.message(CommandStart())
async def cmd_start(m: Message, state: FSMContext):
    await state.clear()
    if not await check_join(m.from_user.id): return await join_prompt(m)
    await db.get_user(m.from_user.id)
    await m.answer(f"👋 سلام <b>{m.from_user.first_name}</b>!\nبه ربات فروش شماره مجازی خوش آمدید.", reply_markup=await main_kb(m.from_user.id))

@router.callback_query(F.data == "check_join")
async def cb_check_join(cb: CallbackQuery, state: FSMContext):
    if await check_join(cb.from_user.id):
        await cb.message.delete()
        await db.get_user(cb.from_user.id)
        await cb.message.answer(f"👋 سلام <b>{cb.from_user.first_name}</b>!", reply_markup=await main_kb(cb.from_user.id))
    else: await cb.answer("❌ شما هنوز در تمام کانال‌ها عضو نشده‌اید!", show_alert=True)

@router.callback_query(F.data == "home")
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    try: await cb.message.edit_text(f"👋 سلام <b>{cb.from_user.first_name}</b>!", reply_markup=await main_kb(cb.from_user.id))
    except: pass
    await cb.answer()

@router.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    u = await db.get_user(cb.from_user.id)
    txt = f"👤 <b>حساب کاربری</b>\n\n🆔 شناسه: <code>{u['user_id']}</code>\n💰 موجودی: <b>{u['balance']:,}</b> تومان\n🕒 ساعت: <code>{datetime.now().strftime('%H:%M')}</code>\n🛒 خریدها: <b>{u['purchases']}</b>\n💳 مجموع شارژ: <b>{u['total_charged']:,}</b> تومان"
    await cb.message.edit_text(txt, reply_markup=back_kb())
    await cb.answer()

@router.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery):
    txt = f"🎧 <b>پشتیبانی</b>\n\n👑 مالک:\n{OWNER_USERNAME} (ID: {OWNER_ID})\n\n👤 ادمین:\n{ADMIN_USERNAME} (ID: {ADMIN_ID})\n\nممنون که با ما هستید 🌹"
    await cb.message.edit_text(txt, reply_markup=back_kb())
    await cb.answer()

@router.callback_query(F.data == "guide")
async def cb_guide(cb: CallbackQuery):
    await cb.message.edit_text("📚 برای مشاهده آموزش‌ها روی دکمه زیر بزنید:", reply_markup=KB([[B("🔗 ورود به کانال", url=GUIDE_CHANNEL_LINK)], [B("◀️ بازگشت", "home")]]))
    await cb.answer()

@router.callback_query(F.data == "stock")
async def cb_stock(cb: CallbackQuery):
    await cb.message.edit_text("🛒 <b>خرید شماره مجازی</b>\nیک دسته را انتخاب کنید:", reply_markup=cats_kb("scat"))
    await cb.answer()

@router.callback_query(F.data == "buy")
async def cb_buy(cb: CallbackQuery):
    await cb.message.edit_text("🛒 <b>خرید شماره مجازی</b>\nیک دسته را انتخاب کنید:", reply_markup=cats_kb("bcat"))
    await cb.answer()

@router.callback_query(F.data.startswith("scat:") | F.data.startswith("bcat:"))
async def cb_cat(cb: CallbackQuery):
    cat = cb.data.split(":")[1]
    if not await db.get_panels(cat): return await cb.answer("❌ پنلی در این دسته نیست.", show_alert=True)
    await cb.message.edit_text(f"📦 پنل‌های موجود در دسته:", reply_markup=await panels_kb(cat))
    await cb.answer()

@router.callback_query(F.data.startswith("panel:"))
async def cb_panel(cb: CallbackQuery):
    pid = int(cb.data.split(":")[1])
    p = await db.get_panel(pid)
    acc = await db.get_avail_acc(pid)
    if not acc: return await cb.answer("😔 موجودی تمام شده.", show_alert=True)
    u = await db.get_user(cb.from_user.id)
    if u["balance"] < p["price"]: return await cb.answer(f"❌ موجودی کافی نیست.\nموجودی: {u['balance']:,}\nنیاز: {p['price']:,}", show_alert=True)
    await db.sub_bal(cb.from_user.id, p["price"])
    await db.sell_acc(acc["id"], cb.from_user.id)
    try:
        await bot.send_message(int(REPORT_CHANNEL_ID), f"✅ <b>گزارش خرید موفق</b>\n\n▫️ شناسه: <code>{mask_u(cb.from_user.id)}</code>\n▫️ کشور: {p['flag']}\n▫️ پنل: <b>{p['name']}</b>\n🔸 شماره: <code>{mask_p(acc['phone'])}</code>\n▫️ مبلغ: <b>{p['price']:,}</b> تومان\n▫️ تاریخ: <code>{datetime.now().strftime('%Y-%m-%d %H:%M')}</code>\n\n📣 شما نیز می‌توانید با استفاده از دکمه زیر وارد بخش خرید شماره شوید.", reply_markup=KB([[B("🛒 ربات شماره مجازی", url=f"https://t.me/{(await bot.get_me()).username}")]]))
    except Exception as e: log.warning(f"Report failed: {e}")
    txt = f"🎉 خرید موفق!\n\n📱 شماره: <code>{acc['phone']}</code>\n🔐 رمز دوم: <code>{acc['twofa'] or 'ندارد'}</code>\n\nبرای دریافت کد ورود، دکمه زیر را بزنید."
    await cb.message.edit_text(txt, reply_markup=KB([[B("🔑 دریافت کد", f"getcode:{acc['id']}")], [B("🏠 منوی اصلی", "home")]]))
    await cb.answer("✅ خرید موفق!")

@router.callback_query(F.data.startswith("getcode:"))
async def cb_getcode(cb: CallbackQuery):
    aid = int(cb.data.split(":")[1])
    acc = await db.get_acc(aid)
    if not acc or (acc["sold_to"] and acc["sold_to"] != cb.from_user.id): return await cb.answer("⛔", show_alert=True)
    if not acc.get("session"): return await cb.answer("⚠️ نشست منقضی شده.", show_alert=True)
    await cb.answer("⏳ در حال دریافت...")
    try:
        client = TelegramClient(StringSession(acc["session"]), TG_API_ID, TG_API_HASH)
        await client.connect()
        code = None
        for m in await client.get_messages(777000, limit=15):
            if m.text:
                match = re.search(r"\b(\d{5,6})\b", m.text)
                if match: code = match.group(1); break
        await client.disconnect()
        if code:
            extra = f"\n🔐 رمز دوم: <code>{acc['twofa']}</code>" if acc["twofa"] else ""
            await cb.message.answer(f"🔑 کد ورود شما: <code>{code}</code>{extra}", reply_markup=KB([[B("🚪 خروج ربات", f"logout:{aid}")]]))
        else: await cb.message.answer("⚠️ کدی یافت نشد. ابتدا در اپ تلگرام شماره را وارد کنید تا کد بیاید.")
    except Exception as e:
        log.exception(e); await cb.message.answer("⚠️ خطا در دریافت کد.")

@router.callback_query(F.data.startswith("logout:"))
async def cb_logout(cb: CallbackQuery):
    aid = int(cb.data.split(":")[1])
    acc = await db.get_acc(aid)
    if not acc or acc["sold_to"] != cb.from_user.id: return await cb.answer("⛔", show_alert=True)
    await cb.answer("⏳ در حال خروج...")
    if acc.get("session"):
        try:
            client = TelegramClient(StringSession(acc["session"]), TG_API_ID, TG_API_HASH)
            await client.connect()
            if await client.is_user_authorized(): await client.log_out()
            await client.disconnect()
        except: pass
    await db.clear_sess(aid)
    try: await cb.message.edit_text("✅ با موفقیت از اکانت خارج شدید.", reply_markup=None)
    except: pass

@router.callback_query(F.data == "charge")
async def cb_charge(cb: CallbackQuery, state: FSMContext):
    await state.set_state(S.charge_amount)
    await cb.message.edit_text("💰 لطفاً مبلغ مورد نظر (به تومان) را فقط به صورت عدد وارد کنید:", reply_markup=back_kb())
    await cb.answer()

@router.message(S.charge_amount)
async def msg_charge_amount(m: Message, state: FSMContext):
    try:
        amount = int(m.text.strip().replace(",", "").replace(".", ""))
        if amount < 1000: raise ValueError
    except: return await m.answer("❌ عدد نامعتبر.")
    await state.update_data(charge_amount=amount)
    await state.set_state(S.charge_receipt)
    await m.answer(f"💳 <b>درخواست شارژ</b>\n\nمبلغ: <code>{amount:,}</code> تومان\n\nلطفاً مبلغ فوق را به شماره کارت زیر واریز کنید:\n<b>به نام: {CARD_HOLDER}</b>\n<code>{CARD_NUMBER}</code>\n\nسپس <b>عکس رسید</b> را ارسال کنید.\n📌 همراه با رسید، <b>آیدی عددی خودتون</b> رو هم ارسال کنید.")

@router.message(S.charge_receipt, F.photo)
async def msg_charge_receipt(m: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("charge_amount")
    await state.clear()
    await m.answer("✅ رسید شما برای بررسی به مالک ارسال شد.")
    txt = f"💳 <b>درخواست شارژ جدید</b>\n\nآیدی: <code>{m.from_user.id}</code>\nیوزرنیم: @{m.from_user.username if m.from_user.username else 'ندارد'}\nمبلغ: <b>{amount:,}</b> تومان"
    try: await m.bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=txt, reply_markup=KB([[B("✅ تایید شارژ", f"apcharge:{m.from_user.id}:{amount}")]]))
    except: pass

@router.callback_query(F.data.startswith("apcharge:"))
async def cb_apcharge(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID: return await cb.answer("⛔", show_alert=True)
    _, uid_s, amt_s = cb.data.split(":")
    uid, amount = int(uid_s), int(amt_s)
    await db.add_bal(uid, amount)
    u = await db.get_user(uid)
    try: await cb.bot.send_message(uid, f"🎉 حساب شما شارژ شد!\nمبلغ: <b>{amount:,}</b> تومان\nموجودی جدید: <b>{u['balance']:,}</b> تومان")
    except: pass
    await cb.message.edit_caption(caption=(cb.message.caption or "") + "\n\n✅ تایید شد")
    await cb.answer("✅")

@router.callback_query(F.data == "inc_balance")
async def cb_inc_balance(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != OWNER_ID: return await cb.answer("⛔")
    await state.set_state(S.inc_uid)
    await cb.message.answer("👤 آیدی عددی کاربر را وارد کنید:")
    await cb.answer()

@router.message(S.inc_uid)
async def msg_inc_uid(m: Message, state: FSMContext):
    try: uid = int(m.text.strip())
    except: return await m.answer("❌ نامعتبر.")
    await state.update_data(inc_uid=uid)
    await state.set_state(S.inc_amount)
    await m.answer("💰 مبلغ مورد نظر را وارد کنید:")

@router.message(S.inc_amount)
async def msg_inc_amount(m: Message, state: FSMContext):
    try: amount = int(m.text.strip().replace(",", ""))
    except: return await m.answer("❌ نامعتبر.")
    uid = (await state.get_data()).get("inc_uid")
    await db.add_bal(uid, amount)
    u = await db.get_user(uid)
    try: await m.bot.send_message(uid, f"🎉 حساب شما شارژ شد!\nمبلغ: <b>{amount:,}</b> تومان\nموجودی جدید: <b>{u['balance']:,}</b> تومان")
    except: pass
    await state.clear()
    await m.answer("✅ موجودی کاربر افزایش یافت.", reply_markup=await main_kb(m.from_user.id))

@router.callback_query(F.data == "panel_add")
async def cb_panel_add(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in (OWNER_ID, ADMIN_ID): return await cb.answer("⛔")
    await state.set_state(S.p_name)
    await cb.message.answer("🏷 نام پنل را وارد کنید:")
    await cb.answer()

@router.message(S.p_name)
async def msg_p_name(m: Message, state: FSMContext):
    await state.update_data(p_name=m.text.strip())
    await state.set_state(S.p_price)
    await m.answer("💰 قیمت (تومان) را وارد کنید:")

@router.message(S.p_price)
async def msg_p_price(m: Message, state: FSMContext):
    try: price = int(m.text.strip().replace(",", ""))
    except: return await m.answer("❌ نامعتبر.")
    await state.update_data(p_price=price)
    await state.set_state(S.p_cat)
    await m.answer("📂 دسته‌بندی را انتخاب کنید:", reply_markup=cats_kb("pcat"))

@router.callback_query(S.p_cat, F.data.startswith("pcat:"))
async def cb_p_cat(cb: CallbackQuery, state: FSMContext):
    await state.update_data(p_cat=cb.data.split(":")[1])
    await state.set_state(S.p_flag)
    await cb.message.edit_text("🌍 فلگ کشور را وارد کنید (مثلاً 🇺🇸):")
    await cb.answer()

@router.message(S.p_flag)
async def msg_p_flag(m: Message, state: FSMContext):
    d = await state.get_data()
    await db.create_panel(d["p_name"], d["p_price"], d["p_cat"], (m.text or "🌍").strip()[:4])
    await state.clear()
    await m.answer("✅ پنل ایجاد شد.", reply_markup=await main_kb(m.from_user.id))

@router.callback_query(F.data == "panel_del")
async def cb_panel_del(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID: return await cb.answer("⛔", show_alert=True)
    panels = await db.all_panels()
    if not panels: return await cb.answer("❌ پنلی وجود ندارد.", show_alert=True)
    rows = [[B(f"{p['flag']} {p['name']}", f"delp:{p['id']}")] for p in panels]
    rows.append([B("◀️ بازگشت", "home")])
    await cb.message.edit_text("🗑 کدام پنل حذف شود؟", reply_markup=KB(rows))
    await cb.answer()

@router.callback_query(F.data.startswith("delp:"))
async def cb_delp(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID: return await cb.answer("⛔", show_alert=True)
    pid = int(cb.data.split(":")[1])
    p = await db.get_panel(pid)
    if not p: return await cb.answer("❌", show_alert=True)
    await cb.message.edit_text(f"⚠️ حذف پنل <b>{p['name']}</b>؟", reply_markup=KB([[B("✅ بله", f"delyes:{pid}")], [B("❌ انصراف", "home")]]))
    await cb.answer()

@router.callback_query(F.data.startswith("delyes:"))
async def cb_delyes(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID: return await cb.answer("⛔", show_alert=True)
    pid = int(cb.data.split(":")[1])
    await db.del_panel(pid)
    await cb.answer("✅ پنل حذف شد.", show_alert=True)
    try: await cb.message.edit_text(f"👋 سلام <b>{cb.from_user.first_name}</b>!", reply_markup=await main_kb(cb.from_user.id))
    except: pass

@router.callback_query(F.data == "acc_add")
async def cb_acc_add(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id not in (OWNER_ID, ADMIN_ID): return await cb.answer("⛔")
    panels = await db.all_panels()
    if not panels: return await cb.answer("❌ پنلی وجود ندارد.", show_alert=True)
    rows = [[B(f"{p['flag']} {p['name']}", f"accpanel:{p['id']}")] for p in panels]
    rows.append([B("◀️ بازگشت", "home")])
    await state.set_state(S.acc_panel)
    await cb.message.answer("➕ پنل مورد نظر را انتخاب کنید:", reply_markup=KB(rows))
    await cb.answer()

@router.callback_query(S.acc_panel, F.data.startswith("accpanel:"))
async def cb_acc_panel(cb: CallbackQuery, state: FSMContext):
    await state.update_data(panel_id=int(cb.data.split(":")[1]))
    await state.set_state(S.acc_phone)
    await cb.message.edit_text("📱 شماره را با فرمت بین‌المللی بفرستید (مثلاً +98912...):")
    await cb.answer()

@router.message(S.acc_phone)
async def msg_acc_phone(m: Message, state: FSMContext):
    phone = m.text.strip()
    if not phone.startswith("+") or len(phone) < 8: return await m.answer("❌ فرمت نامعتبر.")
    try:
        client = TelegramClient(StringSession(), TG_API_ID, TG_API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        globals()[f"pend_{m.from_user.id}"] = {"client": client, "phone": phone, "hash": sent.phone_code_hash}
        await state.set_state(S.acc_code)
        await m.answer("📨 کد ارسال شده را وارد کنید:")
    except Exception as e: await m.answer(f"❌ خطا: {e}")

@router.message(S.acc_code)
async def msg_acc_code(m: Message, state: FSMContext):
    p = globals().get(f"pend_{m.from_user.id}")
    if not p: return await m.answer("❌ نامعتبر.")
    try: await p["client"].sign_in(phone=p["phone"], code=m.text.strip(), phone_code_hash=p["hash"])
    except SessionPasswordNeededError:
        await state.set_state(S.acc_2fa)
        return await m.answer("🔐 رمز دو مرحله‌ای را وارد کنید:")
    except Exception as e: return await m.answer(f"❌ خطا: {e}")
    await _save_acc(m, state, p, "")

@router.message(S.acc_2fa)
async def msg_acc_2fa(m: Message, state: FSMContext):
    p = globals().get(f"pend_{m.from_user.id}")
    if not p: return await m.answer("❌ نامعتبر.")
    pw = m.text.strip()
    try: await p["client"].sign_in(password=pw)
    except Exception as e: return await m.answer(f"❌ خطا: {e}")
    await _save_acc(m, state, p, pw)

async def _save_acc(m: Message, state: FSMContext, pending: dict, twofa: str):
    d = await state.get_data()
    sess = pending["client"].session.save()
    await db.add_acc(d["panel_id"], pending["phone"], sess, twofa)
    try: await pending["client"].disconnect()
    except: pass
    globals().pop(f"pend_{m.from_user.id}", None)
    await state.clear()
    await m.answer("✅ اکانت با موفقیت اضافه شد!", reply_markup=await main_kb(m.from_user.id))

async def main():
    await db.init()
    dp = Dispatcher()
    dp.include_router(router)
    log.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): log.info("stopped")
