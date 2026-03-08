import os
import asyncio
import sqlite3
import random
import string
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

FORCE_CHANNEL = os.getenv("FORCE_CHANNEL")
STORAGE_CHANNEL = int(os.getenv("STORAGE_CHANNEL"))
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Client(
    "filesharebot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS files(code TEXT,message_id INTEGER)")
db.commit()

upload_sessions = {}
broadcast_mode = False


def add_user(uid):
    try:
        cursor.execute("INSERT INTO users VALUES(?)", (uid,))
        db.commit()
    except:
        pass


def get_users():
    cursor.execute("SELECT user_id FROM users")
    return cursor.fetchall()


def save_file(code, msg_id):
    cursor.execute("INSERT INTO files VALUES(?,?)", (code, msg_id))
    db.commit()


def get_files(code):
    cursor.execute("SELECT message_id FROM files WHERE code=?", (code,))
    return cursor.fetchall()


def generate_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


async def progress(current, total, message):
    percent = current * 100 / total
    bar = "█" * int(percent / 10) + "░" * (10 - int(percent / 10))

    try:
        await message.edit_text(
            f"Uploading...\n[{bar}] {percent:.1f}%"
        )
    except:
        pass


async def check_join(client, user_id):
    try:
        await client.get_chat_member(FORCE_CHANNEL, user_id)
        return True
    except:
        return False


@bot.on_message(filters.command("start"))
async def start(client, message):

    user_id = message.from_user.id
    add_user(user_id)

    args = message.text.split()

    if len(args) > 1:

        code = args[1]

        if not await check_join(client, user_id):

            btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("Join Channel", url=f"https://t.me/{FORCE_CHANNEL.replace('@','')}")],
                [InlineKeyboardButton("Check Join", callback_data=f"check_{code}")]
            ])

            return await message.reply_text(
                "Join channel dulu untuk melihat file",
                reply_markup=btn
            )

        files = get_files(code)

        for f in files:

            await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=STORAGE_CHANNEL,
                message_id=f[0]
            )

            await asyncio.sleep(0.2)

        return

    buttons = [
        [InlineKeyboardButton("📤 Upload Video", callback_data="upload")]
    ]

    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")])

    await message.reply_text(
        "File Share Bot\n\nUpload banyak video jadi 1 link",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@bot.on_callback_query(filters.regex("upload"))
async def upload_btn(client, query):

    upload_sessions[query.from_user.id] = []

    await query.message.reply_text(
        "Kirim semua video\n\nJika selesai kirim /done"
    )


@bot.on_message(filters.video | filters.document)
async def upload_file(client, message):

    uid = message.from_user.id

    if uid not in upload_sessions:
        return

    status = await message.reply_text("Uploading...")

    try:

        sent = await client.copy_message(
            chat_id=STORAGE_CHANNEL,
            from_chat_id=message.chat.id,
            message_id=message.id
        )

        upload_sessions[uid].append(sent.message_id)

        await status.edit_text("✅ File tersimpan")

    except Exception as e:

        await status.edit_text(f"Upload gagal\n{e}")


@bot.on_message(filters.command("done"))
async def done(client, message):

    uid = message.from_user.id

    if uid not in upload_sessions:
        return

    files = upload_sessions[uid]

    if not files:
        return await message.reply_text("Tidak ada file")

    code = generate_code()

    for f in files:
        save_file(code, f)

    bot_info = await bot.get_me()

    link = f"https://t.me/{bot_info.username}?start={code}"

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Open Link", url=link)]
    ])

    await message.reply_text(
        f"✅ Link berhasil dibuat\n\n{link}\n\nCode:\n`{code}`",
        reply_markup=btn
    )

    del upload_sessions[uid]


@bot.on_callback_query(filters.regex("broadcast"))
async def broadcast_btn(client, query):

    if query.from_user.id != ADMIN_ID:
        return

    global broadcast_mode
    broadcast_mode = True

    await query.message.reply_text("Kirim pesan untuk broadcast")


@bot.on_message(filters.private)
async def broadcast(client, message):

    global broadcast_mode

    if not broadcast_mode:
        return

    if message.from_user.id != ADMIN_ID:
        return

    users = get_users()

    success = 0
    fail = 0

    msg = await message.reply_text("Broadcast dimulai...")

    for user in users:

        try:

            await message.copy(user[0])
            success += 1

        except:

            fail += 1

        await asyncio.sleep(0.05)

    await msg.edit_text(
        f"Broadcast selesai\n\nSuccess: {success}\nFail: {fail}"
    )

    broadcast_mode = False


@bot.on_callback_query(filters.regex("check_"))
async def check_join_btn(client, query):

    code = query.data.split("_")[1]

    if not await check_join(client, query.from_user.id):
        return await query.answer("Belum join channel", show_alert=True)

    files = get_files(code)

    for f in files:

        await client.copy_message(
            chat_id=query.message.chat.id,
            from_chat_id=STORAGE_CHANNEL,
            message_id=f[0]
        )


bot.run()
