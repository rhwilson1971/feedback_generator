import unittest
from unittest.mock import patch

from bson import ObjectId

import app as app_module


class FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find_one(self, query):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)


def make_tpl(container_id, body, dropdown=()):
    names = app_module._parse_placeholders_from_body(body)
    return {
        "_id": ObjectId(), "name": body, "body": body, "container_id": container_id,
        "placeholders": [
            {"name": n, "input_type": "dropdown" if n in dropdown else "text",
             "options": ["Good", "Great"] if n in dropdown else []}
            for n in names
        ],
    }


class PlaceholderMruTests(unittest.TestCase):
    def setUp(self):
        app_module._placeholder_mru.clear()
        self.c1, self.c2 = ObjectId(), ObjectId()
        self.t1 = make_tpl(self.c1, "Hi {name}, {grade}", dropdown=("grade",))
        self.t2 = make_tpl(self.c1, "Well done {name}")
        self.t3 = make_tpl(self.c2, "Bye {name}")
        patcher = patch.object(
            app_module, "get_templates_collection",
            return_value=FakeCollection([self.t1, self.t2, self.t3]),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def generate(self, tpl, **values):
        return self.client.post(
            f"/templates/{tpl['_id']}/generate",
            data={f"ph_{k}": v for k, v in values.items()},
        )

    def form(self, tpl):
        return self.client.get(f"/templates/{tpl['_id']}/generate").get_data(as_text=True)

    def test_values_are_suggested_for_other_templates_in_same_container(self):
        self.generate(self.t1, name="Tom", grade="Good")
        html = self.form(self.t2)
        self.assertIn('list="mru_name"', html)
        self.assertIn('<option value="Tom">', html)

    def test_other_containers_do_not_see_the_values(self):
        self.generate(self.t1, name="Tom", grade="Good")
        self.assertNotIn("Tom", self.form(self.t3))

    def test_most_recent_first_without_duplicates(self):
        for n in ("Tom", "Ana", "Tom"):
            self.generate(self.t2, name=n)
        self.assertEqual(app_module._placeholder_mru[(self.c1, "name")], ["Tom", "Ana"])

    def test_list_is_capped(self):
        for i in range(app_module.MRU_LIMIT + 5):
            self.generate(self.t2, name=f"S{i}")
        values = app_module._placeholder_mru[(self.c1, "name")]
        self.assertEqual(len(values), app_module.MRU_LIMIT)
        self.assertEqual(values[0], f"S{app_module.MRU_LIMIT + 4}")

    def test_blank_and_dropdown_values_are_not_remembered(self):
        self.generate(self.t1, name="  ", grade="Good")
        self.assertEqual(app_module._placeholder_mru, {})

    def test_no_datalist_before_any_values(self):
        self.assertNotIn("datalist", self.form(self.t2))


if __name__ == "__main__":
    unittest.main()
