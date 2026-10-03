"""In-memory Mongo boundary for route tests and isolated browser fixtures."""
from copy import deepcopy
from types import SimpleNamespace

from bson import ObjectId
from pymongo.errors import DuplicateKeyError


class Cursor(list):
    def sort(self, key, direction):
        """Return a new cursor sorted by key, descending when direction is -1."""
        return Cursor(sorted(self, key=lambda d: d.get(key, 0), reverse=direction == -1))


class Collection:
    def __init__(self, docs=()):
        """Copy initial documents and start with no simulated unique indexes."""
        self.docs = deepcopy(list(docs))
        self.unique_keys = set()

    def matches(self, doc, query):
        """Match every query field by equality; an empty query matches all documents."""
        return all(doc.get(k) == v for k, v in (query or {}).items())

    def find(self, query=None):
        """Return independent copies of matching documents in a sortable cursor."""
        return Cursor(deepcopy(d) for d in self.docs if self.matches(d, query))

    def find_one(self, query=None, sort=None):
        """Return the first match after optional sorting by the first sort specification."""
        docs = self.find(query)
        if sort:
            docs = docs.sort(*sort[0])
        return docs[0] if docs else None

    def count_documents(self, query):
        """Count documents matching the equality query."""
        return len(self.find(query))

    def create_index(self, key, unique=False):
        """Record a unique field constraint when requested; ignore nonunique indexes."""
        if unique:
            self.unique_keys.add(key)

    def check_unique(self, doc, exclude=None):
        """Raise DuplicateKeyError for a conflicting indexed value, excluding one ID if given."""
        for key in self.unique_keys:
            if any(d.get(key) == doc.get(key) and d['_id'] != exclude for d in self.docs):
                raise DuplicateKeyError('duplicate')

    def insert_one(self, doc):
        """Copy and insert a document with a generated ID after checking unique constraints."""
        doc = deepcopy(doc)
        doc.setdefault('_id', ObjectId())
        self.check_unique(doc)
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc['_id'])

    def update_one(self, query, update, upsert=False):
        """Apply $set and $unset to the first match, or insert query and $set fields on upsert."""
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
        """Remove the first matching document and report whether a deletion occurred."""
        for i, doc in enumerate(self.docs):
            if self.matches(doc, query):
                self.docs.pop(i)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    def distinct(self, key):
        """Return distinct scalar values or list items for a field across stored documents."""
        values = set()
        for doc in self.docs:
            value = doc.get(key, [])
            values.update(value if isinstance(value, list) else [value])
        return list(values)
