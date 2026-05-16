from pymongo import MongoClient

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient("localhost", 27017)
    return _client


def get_db():
    return get_client()["feedback_generator"]


def get_templates_collection():
    return get_db()["templates"]
