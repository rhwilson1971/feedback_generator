import os

from pymongo import MongoClient

_client = None

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db():
    return get_client()["feedback_generator"]


def get_templates_collection():
    return get_db()["templates"]
