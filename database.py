import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)
db = conn.cursor()

db.execute("""
CREATE TABLE IF NOT EXISTS files(
batch TEXT,
message_id INTEGER
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER
)
""")

conn.commit()


def save_file(batch, msg):
    db.execute("INSERT INTO files VALUES(?,?)",(batch,msg))
    conn.commit()


def get_files(batch):
    db.execute("SELECT message_id FROM files WHERE batch=?",(batch,))
    return db.fetchall()


def add_user(user):
    db.execute("INSERT OR IGNORE INTO users VALUES(?)",(user,))
    conn.commit()


def get_users():
    db.execute("SELECT user_id FROM users")
    return db.fetchall()
