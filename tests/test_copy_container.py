import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from bson import ObjectId

import app as app_module


class FakeCursor(list):
    def sort(self, key, direction):
        return FakeCursor(sorted(self, key=lambda d: d.get(key, 0), reverse=direction == -1))


class FakeCollection:
    """Minimal stand-in for a Mongo collection: equality queries and sort."""

    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _matches(self, doc, query):
        return all(doc.get(k) == v for k, v in (query or {}).items())

    def find(self, query=None):
        return FakeCursor(d for d in self.docs if self._matches(d, query))

    def find_one(self, query=None, sort=None):
        matches = self.find(query)
        if sort:
            matches = matches.sort(*sort[0])
        return matches[0] if matches else None

    def insert_one(self, doc):
        doc = {**doc, "_id": ObjectId()}
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc["_id"])


class CopyContainerTests(unittest.TestCase):
    def setUp(self):
        old = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.src = {"_id": ObjectId(), "name": "Essays", "category": "Writing", "sort_order": 0}
        self.other = {"_id": ObjectId(), "name": "Labs", "category": "Science", "sort_order": 1}
        self.tpls = [
            {"_id": ObjectId(), "name": name, "body": f"{name} {{student}}",
             "placeholders": [{"name": "student", "input_type": "text"}],
             "container_id": self.src["_id"], "sort_order": order,
             "created_at": old, "updated_at": old}
            for name, order in (("Second", 7), ("First", 2))
        ]
        self.lab_tpl = {"_id": ObjectId(), "name": "Lab", "body": "x", "placeholders": [],
                        "container_id": self.other["_id"], "sort_order": 9}
        self.templates = FakeCollection(self.tpls + [self.lab_tpl])
        self.containers = FakeCollection([self.src, self.other])
        for name, coll in (
            ("get_templates_collection", self.templates),
            ("get_containers_collection", self.containers),
        ):
            patcher = patch.object(app_module, name, return_value=coll)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def copy(self, name="Essays 2026", container_id=None):
        return self.client.post(
            f"/containers/{container_id or self.src['_id']}/copy", data={"name": name}
        )

    def new_container(self):
        (new,) = [c for c in self.containers.docs if c["_id"] not in (self.src["_id"], self.other["_id"])]
        return new

    def new_templates(self, cid):
        return sorted(
            (t for t in self.templates.docs if t["container_id"] == cid),
            key=lambda t: t["sort_order"],
        )

    def test_creates_new_container_with_name_category_and_end_order(self):
        resp = self.copy()
        self.assertEqual(resp.status_code, 302)
        new = self.new_container()
        self.assertEqual(new["name"], "Essays 2026")
        self.assertEqual(new["category"], "Writing")
        self.assertEqual(new["sort_order"], 2)

    def test_copies_all_templates_in_order(self):
        self.copy()
        copies = self.new_templates(self.new_container()["_id"])
        self.assertEqual([t["name"] for t in copies], ["First", "Second"])
        self.assertEqual([t["sort_order"] for t in copies], [10, 11])
        self.assertEqual(copies[0]["body"], "First {student}")
        self.assertEqual(copies[0]["placeholders"], self.tpls[1]["placeholders"])
        self.assertIsNot(copies[0]["placeholders"], self.tpls[1]["placeholders"])
        self.assertGreater(copies[0]["created_at"], self.tpls[1]["created_at"])

    def test_source_is_unchanged(self):
        self.copy()
        self.assertEqual(len(self.new_templates(self.src["_id"])), 2)
        self.assertEqual(len(self.templates.docs), 5)

    def test_blank_name_defaults_to_copy_suffix(self):
        self.copy(name="  ")
        self.assertEqual(self.new_container()["name"], "Essays (copy)")

    def test_empty_container_copies_without_templates(self):
        empty = {"_id": ObjectId(), "name": "Empty", "category": "Default", "sort_order": 5}
        self.containers.docs.append(empty)
        self.copy(container_id=empty["_id"])
        self.assertEqual(len(self.containers.docs), 4)
        self.assertEqual(len(self.templates.docs), 3)

    def test_unknown_and_invalid_ids_are_rejected(self):
        for cid in (ObjectId(), "not-an-id"):
            resp = self.copy(container_id=cid)
            self.assertEqual(resp.status_code, 302)
        self.assertEqual(len(self.containers.docs), 2)
        self.assertEqual(len(self.templates.docs), 3)

    def test_get_is_not_allowed(self):
        resp = self.client.get(f"/containers/{self.src['_id']}/copy")
        self.assertEqual(resp.status_code, 405)


if __name__ == "__main__":
    unittest.main()
