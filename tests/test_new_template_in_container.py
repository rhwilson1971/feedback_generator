import re
import unittest
from unittest.mock import patch

from bson import ObjectId

import app as app_module


class FakeCursor(list):
    def sort(self, key, direction):
        return FakeCursor(sorted(self, key=lambda d: d.get(key, 0), reverse=direction == -1))


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query=None):
        return FakeCursor(self.docs)


class NewTemplateInContainerTests(unittest.TestCase):
    def setUp(self):
        self.c1 = {"_id": ObjectId(), "name": "Essays", "sort_order": 0}
        self.c2 = {"_id": ObjectId(), "name": "Labs", "sort_order": 1}
        patcher = patch.object(
            app_module, "get_containers_collection",
            return_value=FakeCollection([self.c1, self.c2]),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def selected_values(self, query=""):
        html = self.client.get(f"/templates/new{query}").get_data(as_text=True)
        return re.findall(r'<option value="([^"]*)"\s+selected>', html)

    def test_container_from_query_string_is_preselected(self):
        self.assertEqual(self.selected_values(f"?container_id={self.c2['_id']}"), [str(self.c2["_id"])])

    def test_no_container_defaults_to_uncategorized(self):
        self.assertEqual(self.selected_values(), [])

    def test_unknown_container_is_ignored(self):
        self.assertEqual(self.selected_values(f"?container_id={ObjectId()}"), [])
        self.assertEqual(self.selected_values("?container_id=junk"), [])


if __name__ == "__main__":
    unittest.main()
