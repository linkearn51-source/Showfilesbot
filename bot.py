import uuid
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

from config import *
from database import conn, cur

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

user_upload = {}

# --------------------
# FORCE JOIN
# --------------------

async def check_join(user_id):

    try:

        member = await bot.get_chat_member(FORCE_GROUP, user_id)

        if member.status in ["member","administrator","creator"]:
            return True

    except:
        pass

    return False


def join_btn():

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton(
            "JOIN GROUP",
            url=f"https://t.me/{FORCE_GROUP.replace('@','')}"
        )
    )

    kb.add(
        InlineKeyboardButton(
            "VERIFY",
            callback_data="verify"
        )
    )

    return kb


# --------------------
# START
# --------------------

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):

    uid = msg.from_user.id

    cur.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    conn.commit()

    args = msg.get_args()

    if not await check_join(uid):

        await msg.answer(
            "Silahkan join group dulu",
            reply_markup=join_btn()
        )
        return

    if args:

        cur.execute("SELECT file_id FROM links WHERE code=?",(args,))
        files = cur.fetchall()

        file_list = [i[0] for i in files]

        await send_files(msg.chat.id,file_list,0)

        return

    kb = InlineKeyboardMarkup()

    kb.add(
        InlineKeyboardButton("UPLOAD",callback_data="upload"),
        InlineKeyboardButton("CREATE LINK",callback_data="create")
    )

    await msg.answer(
        "FILE STORE BOT",
        reply_markup=kb
    )


# --------------------
# VERIFY JOIN
# --------------------

@dp.callback_query_handler(lambda c: c.data=="verify")
async def verify(call: types.CallbackQuery):

    if await check_join(call.from_user.id):

        await call.message.edit_text(
            "Verified. Bot bisa digunakan"
        )

    else:

        await call.answer(
            "Belum join group",
            show_alert=True
        )


# --------------------
# UPLOAD
# --------------------

@dp.callback_query_handler(lambda c: c.data=="upload")
async def upload(call: types.CallbackQuery):

    user_upload[call.from_user.id] = []

    await call.message.answer(
        "Upload file/video sekarang"
    )


# --------------------
# SAVE FILE
# --------------------

@dp.message_handler(content_types=['video','document','photo'])
async def save(msg: types.Message):

    uid = msg.from_user.id

    if uid not in user_upload:
        return

    progress = await msg.reply("Uploading...")

    sent = await msg.copy_to(DATABASE_CHANNEL)

    user_upload[uid].append(sent.message_id)

    await progress.edit_text(
        f"Uploaded {len(user_upload[uid])} file"
    )


# --------------------
# CREATE LINK
# --------------------

@dp.callback_query_handler(lambda c: c.data=="create")
async def create(call: types.CallbackQuery):

    uid = call.from_user.id

    files = user_upload.get(uid)

    if not files:

        await call.answer("Upload dulu")
        return

    code = str(uuid.uuid4())[:8]

    for f in files:

        cur.execute(
            "INSERT INTO links VALUES(?,?)",
            (code,f)
        )

    conn.commit()

    me = await bot.get_me()

    link = f"https://t.me/{me.username}?start={code}"

    await call.message.answer(
        f"LINK KAMU\n\n{link}"
    )


# --------------------
# SEND FILE PAGINATION
# --------------------

async def send_files(chat_id,files,page):

    per_page = 10

    start = page*per_page
    end = start+per_page

    current = files[start:end]

    for f in current:

        await bot.copy_message(
            chat_id,
            DATABASE_CHANNEL,
            f
        )

        await asyncio.sleep(0.4)

    total = (len(files)-1)//per_page

    kb = InlineKeyboardMarkup()

    if page>0:
        kb.insert(
            InlineKeyboardButton(
                "PREV",
                callback_data=f"page_{page-1}"
            )
        )

    if page<total:
        kb.insert(
            InlineKeyboardButton(
                "NEXT",
                callback_data=f"page_{page+1}"
            )
        )

    kb.add(
        InlineKeyboardButton(
            "JOIN GROUP",
            url=f"https://t.me/{FORCE_GROUP.replace('@','')}"
        )
    )

    await bot.send_message(
        chat_id,
        f"Page {page+1}/{total+1}",
        reply_markup=kb
    )


# --------------------
# BROADCAST
# --------------------

@dp.message_handler(commands=['broadcast'])
async def bc(msg: types.Message):

    if msg.from_user.id != ADMIN_ID:
        return

    text = msg.get_args()

    cur.execute("SELECT id FROM users")

    users = cur.fetchall()

    for u in users:

        try:

            await bot.send_message(u[0],text)

            await asyncio.sleep(0.3)

        except:
            pass

    await msg.answer("Broadcast selesai")


# --------------------

if __name__ == "__main__":
    executor.start_polling(dp)
