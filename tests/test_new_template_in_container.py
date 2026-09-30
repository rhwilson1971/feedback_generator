import re
import unittest
from unittest.mock import patch

from bson import ObjectId

import app as app_module


class FakeCursor(list):
    def sort(self, key, direction):
        """Return a new cursor sorted by key, descending when direction is -1."""
        return FakeCursor(sorted(self, key=lambda d: d.get(key, 0), reverse=direction == -1))


class FakeCollection:
    def __init__(self, docs):
        """Store the documents returned by this fake collection."""
        self.docs = docs

    def find(self, query=None):
        """Return all stored documents as a cursor, ignoring the query."""
        return FakeCursor(self.docs)

    def distinct(self, key):
        """Return the unique values of a list field across stored documents."""
        return sorted({v for d in self.docs for v in d.get(key, [])})


class NewTemplateInContainerTests(unittest.TestCase):
    def setUp(self):
        """Stub two containers and create a Flask client for each test."""
        self.c1 = {"_id": ObjectId(), "name": "Essays", "sort_order": 0}
        self.c2 = {"_id": ObjectId(), "name": "Labs", "sort_order": 1}
        patcher = patch.object(
            app_module, "get_containers_collection",
            return_value=FakeCollection([self.c1, self.c2]),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(
            app_module, "get_templates_collection", return_value=FakeCollection([])
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def selected_values(self, query=""):
        """Return explicitly selected option values from the new template form."""
        html = self.client.get(f"/templates/new{query}").get_data(as_text=True)
        return re.findall(r'<option value="([^"]*)"\s+selected>', html)

    def test_container_from_query_string_is_preselected(self):
        """Verify that a known container ID selects its option in the form."""
        self.assertEqual(self.selected_values(f"?container_id={self.c2['_id']}"), [str(self.c2["_id"])])

    def test_no_container_defaults_to_uncategorized(self):
        """Verify that omitting the container leaves the default option active."""
        self.assertEqual(self.selected_values(), [])

    def test_unknown_container_is_ignored(self):
        """Verify that unknown and malformed IDs leave the default option active."""
        self.assertEqual(self.selected_values(f"?container_id={ObjectId()}"), [])
        self.assertEqual(self.selected_values("?container_id=junk"), [])


if __name__ == "__main__":
    unittest.main()
