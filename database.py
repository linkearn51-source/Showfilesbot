from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(MONGO_URI)
db = client["filestore"]

files = db["files"]
links = db["links"]
users = db["users"]
