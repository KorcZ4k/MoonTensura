import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI")

if not uri:
    raise RuntimeError("MONGODB_URI não encontrada no .env")

client = MongoClient(
    uri,
    tls=True,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
)

db = client[os.getenv("MONGODB_DATABASE")]


try:
    print("MongoDB conectado!")
except Exception as e:
    print("ERRO:")
    print(repr(e))