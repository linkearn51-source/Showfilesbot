import sqlite3

conn = sqlite3.connect("database.db")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS links(code TEXT,file_id INTEGER)")

conn.commit()
