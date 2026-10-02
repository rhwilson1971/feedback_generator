import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId

import app as app_module
from test_copy_container import FakeCollection as BaseFake


class FakeCollection(BaseFake):
    """Adds the update and distinct calls the tag routes use."""

    def update_one(self, query, update):

        """Apply a $set update to the first matching document."""
        doc = self.find_one(query)
        doc.update(update["$set"])

    def distinct(self, key):

        """Return the unique values of a list field across stored documents."""
        return list({v for d in self.docs for v in d.get(key, [])})


class ParseTagsTests(unittest.TestCase):
    def test_splits_trims_and_dedupes_case_insensitively(self):
        """Verify tags are trimmed, blanks dropped and case-insensitive duplicates removed."""
        self.assertEqual(
            app_module._parse_tags(" praise,Late  work, , PRAISE,late work "),
            ["praise", "Late work"],
        )

    def test_blank_gives_no_tags(self):

        """Verify an empty tags field gives no tags."""
        self.assertEqual(app_module._parse_tags(""), [])


class TemplateTagRouteTests(unittest.TestCase):
    def setUp(self):
        from ranking_support import Collection
        scales_patcher = patch("database.get_ranking_scales_collection", return_value=Collection())
        scales_patcher.start()
        self.addCleanup(scales_patcher.stop)
        settings_patcher = patch.object(app_module, "get_settings_collection")
        settings_patcher.start().find_one.return_value = {}
        self.addCleanup(settings_patcher.stop)
        """Stub one tagged and one untagged template in a container."""
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.ctr = {"_id": ObjectId(), "name": "Essays", "category": "W", "sort_order": 0}
        self.tpl = {
            "_id": ObjectId(), "name": "Praise", "body": "Nice {name}",
            "placeholders": [{"name": "name", "input_type": "text", "options": []}],
            "tags": ["praise", "Essay"], "container_id": self.ctr["_id"],
            "sort_order": 0, "created_at": now, "updated_at": now,
        }
        self.old = {**self.tpl, "_id": ObjectId(), "name": "Old", "sort_order": 1}
        self.old.pop("tags")
        self.templates = FakeCollection([self.tpl, self.old])
        self.containers = FakeCollection([self.ctr])
        for name, coll in (
            ("get_templates_collection", self.templates),
            ("get_containers_collection", self.containers),
        ):
            patcher = patch.object(app_module, name, return_value=coll)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def form(self, **extra):

        """Return template form data, with overrides."""
        return {"name": "New", "body": "Hi {name}", "container_id": "", **extra}

    def test_create_saves_parsed_tags(self):

        """Verify creating a template stores its parsed tags."""
        self.client.post("/templates", data=self.form(tags="late, Late, rubric"))
        new = self.templates.find_one({"name": "New"})
        self.assertEqual(new["tags"], ["late", "rubric"])

    def test_update_replaces_tags(self):

        """Verify updating a template replaces its tags."""
        self.client.post(f"/templates/{self.tpl['_id']}/update", data=self.form(tags="rubric"))
        self.assertEqual(self.tpl["tags"], ["rubric"])

    def test_copy_template_keeps_tags(self):

        """Verify copying a template copies its tags without aliasing."""
        self.client.post(f"/templates/{self.tpl['_id']}/copy", data={"container_id": ""})
        copy = self.templates.find_one({"container_id": None})
        self.assertEqual(copy["tags"], ["praise", "Essay"])
        self.assertIsNot(copy["tags"], self.tpl["tags"])

    def test_copy_container_keeps_tags_and_handles_untagged(self):

        """Verify copying a container copies tags, using [] for untagged templates."""
        self.client.post(f"/containers/{self.ctr['_id']}/copy", data={"name": "Copy"})
        new_ctr = self.containers.find_one({"name": "Copy"})
        copies = self.templates.find({"container_id": new_ctr["_id"]}).sort("sort_order", 1)
        self.assertEqual([c["tags"] for c in copies], [["praise", "Essay"], []])

    def test_index_lists_tags_and_row_data(self):

        """Verify the index renders the tag filter, row tag data and badges."""
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn('class="form-check-input tag-filter-option" type="checkbox"\n                 value="Essay"', html)
        self.assertIn("data-tags=\"[&#34;praise&#34;, &#34;Essay&#34;]\"", html)
        self.assertIn('data-tags="[]"', html)
        self.assertIn('tag-badge ms-1">praise<', html)

    def test_index_hides_tag_filter_without_tags(self):

        """Verify the tag filter is hidden when no template has tags."""
        self.tpl.pop("tags")
        self.assertNotIn("tagFilterForm", self.client.get("/").get_data(as_text=True))

    def test_edit_form_prefills_tags_and_offers_existing(self):

        """Verify the edit form prefills tags and offers existing ones."""
        html = self.client.get(f"/templates/{self.tpl['_id']}/edit").get_data(as_text=True)
        self.assertIn('value="praise, Essay"', html)
        self.assertIn('data-tag="Essay"', html)


if __name__ == "__main__":
    unittest.main()
