import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId

import app as app_module


class FakeCollection:
    """Minimal stand-in for a Mongo collection: equality queries and sort."""

    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def _matches(self, doc, query):
        return all(doc.get(k) == v for k, v in (query or {}).items())

    def find_one(self, query=None, sort=None):
        matches = [d for d in self.docs if self._matches(d, query)]
        if sort:
            key, direction = sort[0]
            matches.sort(key=lambda d: d.get(key, 0), reverse=direction == -1)
        return matches[0] if matches else None

    def insert_one(self, doc):
        doc = {**doc, "_id": ObjectId()}
        self.docs.append(doc)


class CopyTemplateTests(unittest.TestCase):
    def setUp(self):
        self.ctr_a = {"_id": ObjectId(), "name": "Essays", "category": "Writing"}
        self.ctr_b = {"_id": ObjectId(), "name": "Labs", "category": "Science"}
        self.source = {
            "_id": ObjectId(),
            "name": "Great work",
            "body": "Well done, {student}!",
            "placeholders": [{"name": "student", "type": "text"}],
            "container_id": self.ctr_a["_id"],
            "sort_order": 4,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
        self.templates = FakeCollection([self.source])
        self.containers = FakeCollection([self.ctr_a, self.ctr_b])
        for name, coll in (
            ("get_templates_collection", self.templates),
            ("get_containers_collection", self.containers),
        ):
            patcher = patch.object(app_module, name, return_value=coll)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def copy(self, container_id, template_id=None):
        return self.client.post(
            f"/templates/{template_id or self.source['_id']}/copy",
            data={"container_id": container_id},
        )

    def copies(self):
        return [d for d in self.templates.docs if d["_id"] != self.source["_id"]]

    def test_copy_to_other_container_keeps_name_and_content(self):
        resp = self.copy(str(self.ctr_b["_id"]))
        self.assertEqual(resp.status_code, 302)
        (new,) = self.copies()
        self.assertEqual(new["name"], "Great work")
        self.assertEqual(new["body"], self.source["body"])
        self.assertEqual(new["placeholders"], self.source["placeholders"])
        self.assertEqual(new["container_id"], self.ctr_b["_id"])

    def test_copy_does_not_alias_or_change_the_source(self):
        self.copy(str(self.ctr_b["_id"]))
        (new,) = self.copies()
        self.assertIsNot(new["placeholders"], self.source["placeholders"])
        self.assertEqual(self.source["container_id"], self.ctr_a["_id"])
        self.assertEqual(self.source["name"], "Great work")

    def test_copy_goes_to_end_of_list_with_fresh_timestamps(self):
        self.copy(str(self.ctr_b["_id"]))
        (new,) = self.copies()
        self.assertEqual(new["sort_order"], 5)
        self.assertGreater(new["created_at"], self.source["created_at"])
        self.assertEqual(new["created_at"], new["updated_at"])

    def test_copy_to_same_container_gets_suffix(self):
        self.copy(str(self.ctr_a["_id"]))
        (new,) = self.copies()
        self.assertEqual(new["name"], "Great work (copy)")
        self.assertEqual(new["container_id"], self.ctr_a["_id"])

    def test_name_collision_in_target_gets_suffix(self):
        self.templates.docs.append(
            {"_id": ObjectId(), "name": "Great work", "body": "x",
             "placeholders": [], "container_id": self.ctr_b["_id"], "sort_order": 0}
        )
        self.copy(str(self.ctr_b["_id"]))
        names = [d["name"] for d in self.copies() if d["body"] != "x"]
        self.assertEqual(names, ["Great work (copy)"])

    def test_repeated_copies_get_numbered_suffixes(self):
        self.copy(str(self.ctr_a["_id"]))
        self.copy(str(self.ctr_a["_id"]))
        names = sorted(d["name"] for d in self.copies())
        self.assertEqual(names, ["Great work (copy 2)", "Great work (copy)"])

    def test_empty_container_copies_to_uncategorized(self):
        self.copy("")
        (new,) = self.copies()
        self.assertIsNone(new["container_id"])
        self.assertEqual(new["name"], "Great work")

    def test_unknown_container_is_rejected(self):
        resp = self.copy(str(ObjectId()))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.copies(), [])

    def test_invalid_container_id_is_rejected(self):
        resp = self.copy("not-an-id")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.copies(), [])

    def test_unknown_template_is_rejected(self):
        resp = self.copy(str(self.ctr_b["_id"]), template_id=str(ObjectId()))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.copies(), [])

    def test_invalid_template_id_is_rejected(self):
        resp = self.copy(str(self.ctr_b["_id"]), template_id="nope")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.copies(), [])

    def test_get_is_not_allowed(self):
        resp = self.client.get(f"/templates/{self.source['_id']}/copy")
        self.assertEqual(resp.status_code, 405)


if __name__ == "__main__":
    unittest.main()
