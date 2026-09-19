import unittest
from unittest.mock import patch

import app as app_module


class FakeCollection:
    """Minimal stand-in for the Mongo settings collection."""

    def __init__(self, doc=None):
        self.doc = doc

    def find_one(self, _query):
        return self.doc

    def update_one(self, _query, update, upsert=False):
        self.doc = {**(self.doc or {}), **update["$set"]}


class ThemeSettingTests(unittest.TestCase):
    def setUp(self):
        self.collection = FakeCollection()
        patcher = patch.object(
            app_module, "get_settings_collection", return_value=self.collection
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def test_default_is_system(self):
        self.assertEqual(app_module.get_settings()["theme"], "system")

    def test_stored_value_is_returned(self):
        self.collection.doc = {"theme": "dark"}
        self.assertEqual(app_module.get_settings()["theme"], "dark")

    def test_corrupt_stored_value_falls_back_to_default(self):
        self.collection.doc = {"theme": "purple"}
        self.assertEqual(app_module.get_settings()["theme"], "system")

    def test_post_saves_valid_theme(self):
        self.client.post("/settings", data={"theme": "light"})
        self.assertEqual(self.collection.doc["theme"], "light")

    def test_post_ignores_invalid_theme(self):
        self.collection.doc = {"theme": "dark"}
        self.client.post("/settings", data={"theme": "purple"})
        self.assertEqual(self.collection.doc["theme"], "dark")

    def test_post_without_theme_keeps_existing(self):
        self.collection.doc = {"theme": "light"}
        self.client.post("/settings", data={})
        self.assertEqual(self.collection.doc["theme"], "light")

    def test_html_carries_preference_and_explicit_theme(self):
        self.collection.doc = {"theme": "light"}
        html = self.client.get("/settings").get_data(as_text=True)
        self.assertIn('data-theme-pref="light"', html)
        self.assertIn('data-theme="light"', html)

    def test_system_pref_leaves_data_theme_to_script(self):
        html = self.client.get("/settings").get_data(as_text=True)
        self.assertIn('data-theme-pref="system"', html)
        self.assertNotIn('data-theme="', html)


if __name__ == "__main__":
    unittest.main()
