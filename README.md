# Telegram File Store Bot

Bot Telegram untuk menyimpan file/video dan menghasilkan link share.

## Fitur

- Force Join Group
- Upload file/video
- Simpan otomatis ke channel database
- 1 link untuk banyak file
- Pagination (Prev / Next)
- Broadcast admin

## Deploy Railway

1. Upload project ke GitHub
2. Buka https://railway.app
3. New Project
4. Deploy from GitHub
5. Pilih repository bot

## Environment Variables

Isi di Railway:

BOT_TOKEN=tokenbot
FORCE_GROUP=@groupkamu
DATABASE_CHANNEL=-100xxxxxxxx
ADMIN_ID=123456789

## Jalankan lokal

pip install -r requirements.txt
python main.py
