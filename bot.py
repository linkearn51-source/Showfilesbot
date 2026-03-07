import random
import string
import asyncio

from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant, FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from database import *

app = Client(
    "filesharebot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_batch = {}
user_stats = {}

def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


async def check_join(user):
    try:
        await app.get_chat_member(FORCE_CHANNEL, user)
        return True
    except UserNotParticipant:
        return False
    except:
        return False


# ================= START MENU =================

@app.on_message(filters.command("start"))
async def start(client, message):

    add_user(message.from_user.id)

    args = message.text.split()

    if len(args) == 1:

        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload File", callback_data="upload")],
            [InlineKeyboardButton("📂 Cara Pakai", callback_data="help")],
            [InlineKeyboardButton("📢 Channel", url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}")]
        ])

        await message.reply_text(
            "👋 Selamat datang di Bot File Share\n\n"
            "Kirim video/file untuk membuat link download.",
            reply_markup=buttons
        )
        return

    code = args[1]

    joined = await check_join(message.from_user.id)

    if not joined:

        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("✅ Saya Sudah Join", callback_data=f"check_{code}")]
        ])

        await message.reply_text(
            "⚠️ Kamu harus join channel dulu",
            reply_markup=btn
        )
        return

    await send_files(message, code)


# ================= HELP BUTTON =================

@app.on_callback_query(filters.regex("help"))
async def help_button(client, query):

    await query.message.edit_text(
        "📂 Cara Pakai Bot\n\n"
        "1️⃣ Kirim video/file\n"
        "2️⃣ Bisa kirim banyak file\n"
        "3️⃣ Ketik /done\n"
        "4️⃣ Bot akan membuat link download"
    )


# ================= UPLOAD BUTTON =================

@app.on_callback_query(filters.regex("upload"))
async def upload_button(client, query):

    await query.message.edit_text(
        "📤 Kirim video atau file ke bot.\n\n"
        "Jika sudah selesai kirim /done"
    )


# ================= SEND FILE =================

async def send_files(message, code):

    files = get_files(code)

    if not files:
        await message.reply_text("❌ File tidak ditemukan")
        return

    for f in files:

        try:
            await app.copy_message(
                message.chat.id,
                STORAGE_CHANNEL,
                f[0]
            )

        except FloodWait as e:
            await asyncio.sleep(e.value)


# ================= CHECK JOIN BUTTON =================

@app.on_callback_query(filters.regex("check_"))
async def check(client, query):

    code = query.data.split("_")[1]

    joined = await check_join(query.from_user.id)

    if not joined:
        await query.answer("❌ Kamu belum join", show_alert=True)
        return

    await query.message.delete()

    await send_files(query.message, code)


# ================= UPLOAD FILE =================

@app.on_message(filters.video | filters.document)
async def upload(client, message):

    uid = message.from_user.id

    if uid not in user_batch:

        code = gen_code()

        user_batch[uid] = code
        user_stats[uid] = {"count":0,"size":0}

    else:
        code = user_batch[uid]

    file_size = message.document.file_size if message.document else message.video.file_size

    sent = await message.copy(STORAGE_CHANNEL)

    save_file(code, sent.id)

    user_stats[uid]["count"] += 1
    user_stats[uid]["size"] += file_size

    total_mb = round(user_stats[uid]["size"]/1024/1024,2)

    await message.reply_text(
        f"✅ File ditambahkan\n\n"
        f"📦 Total File : {user_stats[uid]['count']}\n"
        f"💾 Total Size : {total_mb} MB"
    )


# ================= DONE =================

@app.on_message(filters.command("done"))
async def done(client, message):

    uid = message.from_user.id

    if uid not in user_batch:

        await message.reply_text("❌ Tidak ada file")
        return

    code = user_batch[uid]

    link = f"https://t.me/{(await app.get_me()).username}?start={code}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Buka Link", url=link)],
        [InlineKeyboardButton("📋 Copy Code", callback_data=f"code_{code}")]
    ])

    await message.reply_text(
        f"✅ Batch selesai\n\n"
        f"🔑 Code: `{code}`",
        reply_markup=buttons
    )

    del user_batch[uid]
    del user_stats[uid]


# ================= CODE BUTTON =================

@app.on_callback_query(filters.regex("code_"))
async def code_button(client, query):

    code = query.data.split("_")[1]

    files = get_files(code)

    if not files:
        await query.answer("File tidak ditemukan", show_alert=True)
        return

    await send_files(query.message, code)


# ================= CODE TEXT =================

@app.on_message(filters.text & ~filters.command("start"))
async def code_text(client, message):

    code = message.text.strip()

    files = get_files(code)

    if files:
        await send_files(message, code)


print("Bot Running...")
app.run()
