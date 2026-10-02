import unittest
from unittest.mock import patch

from bson import ObjectId

import app as app_module
from test_placeholder_mru import FakeCollection, make_tpl


class GeneratedFeedbackMarkerTests(unittest.TestCase):
    """The browser extension finds generated feedback via this marker."""

    def setUp(self):
        settings_patcher = patch.object(app_module, "get_settings_collection")
        settings_patcher.start().find_one.return_value = {}
        self.addCleanup(settings_patcher.stop)
        self.tpl = make_tpl(ObjectId(), "Hi {name}")
        patcher = patch.object(
            app_module, "get_templates_collection", return_value=FakeCollection([self.tpl])
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()
        self.url = f"/templates/{self.tpl['_id']}/generate"

    def test_marker_present_after_generating(self):
        html = self.client.post(self.url, data={"ph_name": "Tom"}).get_data(as_text=True)
        self.assertIn('id="resultText" rows="6" readonly data-feedback-generated>Hi Tom<', html)

    def test_marker_absent_on_blank_form(self):
        self.assertNotIn("data-feedback-generated", self.client.get(self.url).get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
