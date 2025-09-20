import asyncio
import json
import os
from typing import Optional
from urllib.parse import quote

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    LabeledPrice,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton
)
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# --- FSM imports ---
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ---------- Sozlamalar ----------
BOT_TOKEN = "8211577328:AAEYN_DTrjq0lvkPnDF_ZYEO64vSoX3iXo4"
ADMIN_ID = 2088528834
PROVIDER_TOKEN = ""
DB_PATH = "db.json"
BOT_USERNAME = "bstars_uzbot"
# ---------------------------------

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Tovarlar
ITEMS = {
    "buy_1": {"label": "1 ta 🏀 • 9🌟", "amount": 9, "balls": 1},
    "buy_2": {"label": "2 ta 🏀 • 5🌟", "amount": 5, "balls": 2},
    "buy_3": {"label": "3 ta 🏀 • 7🌟", "amount": 7, "balls": 3},  # ✅ добавлено в меню
    "buy_4": {"label": "4 ta 🏀 • 3🌟", "amount": 3, "balls": 4},
    "buy_5": {"label": "5 ta 🏀 • 1🌟", "amount": 1, "balls": 5},
}

# --- Oddiy JSON DB ---
def load_db():
    if not os.path.exists(DB_PATH):
        return {"balances": {}, "referrals": {}, "credited": {}, "success_on": 4, "success_percent": 50}
    with open(DB_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        data.setdefault("balances", {})
        data.setdefault("referrals", {})
        data.setdefault("credited", {})
        data.setdefault("success_on", data.get("success_on", 4))
        data.setdefault("success_percent", data.get("success_percent", 50))
        return data

def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

DB = load_db()

def get_balance(user_id: int) -> int:
    return DB["balances"].get(str(user_id), 0)

def add_balance(user_id: int, amount: int):
    DB["balances"][str(user_id)] = DB["balances"].get(str(user_id), 0) + amount
    save_db(DB)

def set_referral(referred_id: int, inviter_id: int):
    DB["referrals"][str(referred_id)] = inviter_id
    save_db(DB)

def get_referral(referred_id: int) -> Optional[int]:
    return DB["referrals"].get(str(referred_id))

def is_credited(referred_id: int) -> bool:
    return DB["credited"].get(str(referred_id), False)

def set_credited(referred_id: int):
    DB["credited"][str(referred_id)] = True
    save_db(DB)

def get_success_percent() -> int:
    return DB.get("success_percent", 50)

def set_success_percent(percent: int):
    DB["success_percent"] = percent
    k = round(percent * 6 / 100)
    if k < 0: k = 0
    if k > 6: k = 6
    if k == 0:
        DB["success_on"] = 7
    else:
        DB["success_on"] = 7 - k
    save_db(DB)

def get_success_on() -> int:
    percent = get_success_percent()
    k = round(percent * 6 / 100)
    if k == 0:
        return 7
    return 7 - k

if "success_percent" not in DB:
    stored_on = DB.get("success_on", 4)
    k = max(0, 7 - stored_on) if stored_on <= 6 else 0
    percent = round(k * 100 / 6)
    DB["success_percent"] = percent
    save_db(DB)

# 📌 Asosiy klaviatura
def get_keyboard(user_id=None):
    kb = []

    # первые две строки по 2 кнопки
    kb.append([
        InlineKeyboardButton(text=ITEMS["buy_1"]["label"], callback_data="buy_1"),
        InlineKeyboardButton(text=ITEMS["buy_2"]["label"], callback_data="buy_2"),
    ])
    kb.append([
        InlineKeyboardButton(text=ITEMS["buy_3"]["label"], callback_data="buy_3"),
        InlineKeyboardButton(text=ITEMS["buy_4"]["label"], callback_data="buy_4"),
    ])

    # третья строка: 5 мячей + реферал
    kb.append([
        InlineKeyboardButton(text=ITEMS["buy_5"]["label"], callback_data="buy_5"),
        InlineKeyboardButton(text="+3⭐ Referal", callback_data="referal"),
    ])

    # четвёртая строка: только для админа
    if user_id == ADMIN_ID:
        kb.append([
            InlineKeyboardButton(text="🎛 Chance sozlamalari", callback_data="chance_menu")
        ])

    return InlineKeyboardMarkup(inline_keyboard=kb)

# 🎬 Start komandasi
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    DB["balances"].setdefault(str(user_id), 0)
    save_db(DB)

    balance = get_balance(user_id)

    start_text = (
        "🏀 <b>Basket Starsga xush kelibsiz!</b>\n\n"
        "🏀 Basketbol toplarini oling, o‘ynang va omadingizni sinang 🎁\n\n"
        f"💰 Balansingiz: <b>{balance} ⭐</b>\n\n"
        "⬇️ Shulardan birini tanlang:"
    )
    await message.answer(start_text, reply_markup=get_keyboard(user_id))
# 📌 Tovar sotib olish
@dp.callback_query(F.data.in_(list(ITEMS.keys())))
async def buy_handler(call: types.CallbackQuery):
    key = call.data
    item = ITEMS[key]
    prices = [LabeledPrice(label=item["label"], amount=item["amount"])]
    payload = f"basket:{key}:{item['balls']}:{call.from_user.id}"

    try:
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=f"{item['label']} xaridi",
            description=f"Siz {item['label']} uchun to‘lov qilmoqchisiz.",
            payload=payload,
            provider_token=PROVIDER_TOKEN,
            currency="XTR",
            prices=prices,
            start_parameter="basket_game",
        )
    except Exception:
        await call.message.answer("Hisob-fakturani yaratib bo‘lmadi.")
    await call.answer()

# 📌 To‘lovni tasdiqlash
@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# 📌 O‘yin jarayoni
@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    sp = message.successful_payment
    payload = sp.invoice_payload
    balls = 1
    if payload and payload.startswith("basket:"):
        try:
            parts = payload.split(":")
            balls = int(parts[2])
        except Exception:
            balls = 1

    results, hits = [], 0
    success_on = get_success_on()

    for i in range(balls):
        dice_msg = await bot.send_dice(chat_id=message.chat.id, emoji="🏀")
        value = getattr(dice_msg, "dice", None).value if getattr(dice_msg, "dice", None) else None

        if value is None:
            results.append("❌ o‘tmadi")
        else:
            if success_on <= 6 and value >= success_on:
                results.append(f"✅ kirdi!")
                hits += 1
            else:
                results.append(f"❌ o‘tmadi")

        await asyncio.sleep(0.5)

    await message.answer(
        f"\n📊 <b>O‘yin natijalari</b>\n"
        f"🏀 {balls} ta to‘p\n\n" + "\n".join(results)
    )

# 📌 Referal tugmasi
@dp.callback_query(F.data == "referal")
async def referal_handler(call: types.CallbackQuery):
    user_id = call.from_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"

    text = (
        "🔗 <b>Referal</b>\n\n"
        "<b>Do‘stlaringizni referal havola orqali chaqiring va balansingizga +3⭐ qo‘shing!</b>"
    )

    share_text = "Do‘stim, mana qiziqarli o‘yin!"
    url_text = quote(share_text)
    url_link = quote(ref_link)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ulashish 🔗", url=f"https://t.me/share/url?url={url_link}&text={url_text}")],
        [InlineKeyboardButton(text="📋 Nusxa olish", copy_text=CopyTextButton(text=ref_link))],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")]
    ])

    await call.message.edit_text(text, reply_markup=keyboard)
    await call.answer()

# 📌 Orqaga tugmasi
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(call: types.CallbackQuery, state: FSMContext):
    try:
        await state.clear()
    except Exception:
        pass

    await call.message.edit_text(
        f"🏀 <b>Basket Game’ga xush kelibsiz!</b>\n\n"
        f"💰 <b>Balansingiz:</b> {get_balance(call.from_user.id)} ⭐\n\n⬇️ Paketni tanlang:",
        reply_markup=get_keyboard(call.from_user.id)
    )
    await call.answer()

# 📌 Chance sozlamalari
@dp.callback_query(F.data == "chance_menu")
async def chance_menu(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Faqat admin uchun!")

    current_percent = get_success_percent()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10%", callback_data="chance_10"),
            InlineKeyboardButton(text="25%", callback_data="chance_25"),
            InlineKeyboardButton(text="50%", callback_data="chance_50"),
        ],
        [
            InlineKeyboardButton(text="75%", callback_data="chance_75"),
            InlineKeyboardButton(text="90%", callback_data="chance_90"),
            InlineKeyboardButton(text="100%", callback_data="chance_100"),
        ],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_menu")]
    ])

    await call.message.edit_text(
        f"🎛 <b>Omad sozlamalari</b>\n\n"
        f"✅ Hozirgi qiymat: <b>{current_percent}%</b>\n\n"
        f"Yangi foizni tanlang:",
        reply_markup=kb
    )
    await call.answer()

# 📌 Обработка выбора процента
@dp.callback_query(F.data.startswith("chance_"))
async def set_chance_percent(call: types.CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        return await call.answer("⛔ Faqat admin uchun!")

    value = int(call.data.split("_")[1])
    set_success_percent(value)

    await call.message.edit_text(
        f"✅ Omad foizi o‘rnatildi: <b>{value}%</b>",
        reply_markup=get_keyboard(call.from_user.id)
    )
    await call.answer("O‘zgartirildi!")

# 🔄 Botni ishga tushirish
async def main():
    print("🤖 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())