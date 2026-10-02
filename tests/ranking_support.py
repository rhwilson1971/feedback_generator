"""In-memory Mongo boundary for route tests and isolated browser fixtures."""
from copy import deepcopy
from types import SimpleNamespace

from bson import ObjectId
from pymongo.errors import DuplicateKeyError


class Cursor(list):
    def sort(self, key, direction):
        return Cursor(sorted(self, key=lambda d: d.get(key, 0), reverse=direction == -1))


class Collection:
    def __init__(self, docs=()):
        self.docs = deepcopy(list(docs))
        self.unique_keys = set()

    def matches(self, doc, query):
        return all(doc.get(k) == v for k, v in (query or {}).items())

    def find(self, query=None):
        return Cursor(deepcopy(d) for d in self.docs if self.matches(d, query))

    def find_one(self, query=None, sort=None):
        docs = self.find(query)
        if sort:
            docs = docs.sort(*sort[0])
        return docs[0] if docs else None

    def count_documents(self, query):
        return len(self.find(query))

    def create_index(self, key, unique=False):
        if unique:
            self.unique_keys.add(key)

    def check_unique(self, doc, exclude=None):
        for key in self.unique_keys:
            if any(d.get(key) == doc.get(key) and d['_id'] != exclude for d in self.docs):
                raise DuplicateKeyError('duplicate')

    def insert_one(self, doc):
        doc = deepcopy(doc)
        doc.setdefault('_id', ObjectId())
        self.check_unique(doc)
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc['_id'])

    def update_one(self, query, update, upsert=False):
        for i, doc in enumerate(self.docs):
            if self.matches(doc, query):
                result = {**doc, **deepcopy(update.get('$set', {}))}
                for key in update.get('$unset', {}):
                    result.pop(key, None)
                self.check_unique(result, exclude=doc['_id'])
                self.docs[i] = result
                return SimpleNamespace(matched_count=1)
        if upsert:
            self.insert_one({**query, **update.get('$set', {})})
        return SimpleNamespace(matched_count=0)

    def delete_one(self, query):
        for i, doc in enumerate(self.docs):
            if self.matches(doc, query):
                self.docs.pop(i)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def distinct(self, key):
        values = set()
        for doc in self.docs:
            value = doc.get(key, [])
            values.update(value if isinstance(value, list) else [value])
        return list(values)
