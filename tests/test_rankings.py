import unittest
from unittest.mock import patch

from bson import ObjectId
from werkzeug.datastructures import MultiDict

import app as app_module
from ranking_support import Collection


class RankingScaleTests(unittest.TestCase):
    def setUp(self):
        """Isolate scale routes with in-memory scales, templates, and settings collections."""
        self.scales = Collection()
        self.templates = Collection()
        self.settings = Collection()
        for target, value in [('database.get_ranking_scales_collection', self.scales),
                              ('database.get_templates_collection', self.templates),
                              ('app.get_settings_collection', self.settings)]:
            p = patch(target, return_value=value, create=True)
            p.start()
            self.addCleanup(p.stop)
        self.client = app_module.app.test_client()

    def form(self, name='Completion', ids=('3', '1'), descriptions=('Needs work', 'Completed')):
        """Build submitted scale rows, preserving repeated fields and caller-supplied order."""
        return MultiDict([('name', name)] + [('rank_id', v) for v in ids] +
                         [('rank_description', v) for v in descriptions])

    def create(self, **kwargs):
        """Post a scale form with optional field overrides."""
        return self.client.post('/rankings', data=self.form(**kwargs))

    def seed(self):
        """Insert a two-rank scale and return its ID for route tests."""
        sid = self.scales.insert_one({'name': 'Completion', 'name_key': 'completion',
                                     'ranks': [{'id': 1, 'description': 'Completed'},
                                               {'id': 3, 'description': 'Needs work'}]}).inserted_id
        return sid

    def test_create_stores_sorted_ranks_and_normalized_unique_name(self):
        """Verify creation trims names, stores a normalized key, and orders ranks numerically."""
        response = self.create(name='  Completion  ')
        self.assertEqual(response.status_code, 302)
        scale = self.scales.find_one()
        self.assertEqual(scale['name'], 'Completion')
        self.assertEqual(scale['name_key'], 'completion')
        self.assertEqual([r['id'] for r in scale['ranks']], [1, 3])
        self.assertIn('created_at', scale)

    def test_invalid_inputs_preserve_form_without_saving(self):
        """Verify malformed scale fields return the form with HTTP 400 and save no scale."""
        for kwargs in [dict(name=''), dict(ids=(), descriptions=()),
                       dict(ids=('0',)), dict(ids=('-1',)), dict(ids=('x',)),
                       dict(ids=('1', '01')), dict(descriptions=('', 'ok')),
                       dict(ids=('1',), descriptions=())]:
            with self.subTest(kwargs=kwargs):
                response = self.create(**kwargs)
                self.assertEqual(response.status_code, 400)
                self.assertIn('name="name"', response.get_data(as_text=True))
        self.assertEqual(self.scales.count_documents({}), 0)

    def test_duplicate_names_ignore_case_and_surrounding_whitespace(self):
        """Verify normalized duplicate names are rejected without adding a second scale."""
        self.create()
        response = self.create(name=' completion ')
        self.assertEqual(response.status_code, 400)
        self.assertIn('already exists', response.get_data(as_text=True))
        self.assertEqual(self.scales.count_documents({}), 1)

    def test_list_and_form_render_with_usage_count(self):
        """Verify scale pages show stored values and the count of referencing templates."""
        sid = self.seed()
        self.templates.insert_one({'ranking_scale_id': sid, 'ranking_rank_id': 1})
        html = self.client.get('/rankings').get_data(as_text=True)
        self.assertIn('Completion', html)
        self.assertIn('1 template', html)
        html = self.client.get(f'/rankings/{sid}/edit').get_data(as_text=True)
        self.assertIn('value="Completed"', html)
        self.assertEqual(self.client.get('/rankings/new').status_code, 200)

    def test_rename_and_description_edit_keep_existing_references(self):
        """Verify shared labels can change while an assigned rank ID stays intact."""
        sid = self.seed()
        self.templates.insert_one({'ranking_scale_id': sid, 'ranking_rank_id': 1})
        response = self.client.post(f'/rankings/{sid}/update', data=self.form(
            name='Quality', ids=('1', '3'), descriptions=('Excellent', 'Retry')))
        self.assertEqual(response.status_code, 302)
        scale = self.scales.find_one({'_id': sid})
        self.assertEqual(scale['name'], 'Quality')
        self.assertEqual(scale['ranks'][0]['description'], 'Excellent')
        self.assertEqual(self.templates.find_one()['ranking_rank_id'], 1)

    def test_deleting_used_scale_is_blocked(self):
        """Verify deleting a referenced scale shows a warning and leaves it stored."""
        sid = self.seed()
        self.templates.insert_one({'ranking_scale_id': sid, 'ranking_rank_id': 1})
        response = self.client.post(f'/rankings/{sid}/delete', follow_redirects=True)
        self.assertIn('in use', response.get_data(as_text=True))
        self.assertIsNotNone(self.scales.find_one({'_id': sid}))

    def test_removing_or_renumbering_used_rank_is_blocked(self):
        """Verify replacing an assigned rank number is rejected and preserves the original."""
        sid = self.seed()
        self.templates.insert_one({'ranking_scale_id': sid, 'ranking_rank_id': 1})
        response = self.client.post(f'/rankings/{sid}/update', data=self.form(
            ids=('2', '3'), descriptions=('Changed', 'Retry')))
        self.assertEqual(response.status_code, 400)
        self.assertIn('in use', response.get_data(as_text=True))
        self.assertEqual(self.scales.find_one({'_id': sid})['ranks'][0]['id'], 1)

    def test_unused_rank_and_scale_can_be_removed(self):
        """Verify unused ranks and scales can be deleted after references are cleared."""
        sid = self.seed()
        self.templates.insert_one({'ranking_scale_id': sid, 'ranking_rank_id': 1})
        response = self.client.post(f'/rankings/{sid}/update', data=self.form(
            ids=('1',), descriptions=('Completed',)))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.scales.find_one()['ranks']), 1)
        self.templates.docs.clear()
        self.assertEqual(self.client.post(f'/rankings/{sid}/delete').status_code, 302)
        self.assertIsNone(self.scales.find_one())

    def test_unknown_and_malformed_scale_ids_return_404(self):
        """Verify edit, update, and delete return HTTP 404 for missing or invalid scale IDs."""
        for sid in (str(ObjectId()), 'bad'):
            self.assertEqual(self.client.get(f'/rankings/{sid}/edit').status_code, 404)
            self.assertEqual(self.client.post(f'/rankings/{sid}/update', data=self.form()).status_code, 404)
            self.assertEqual(self.client.post(f'/rankings/{sid}/delete').status_code, 404)

    def test_scale_names_are_escaped(self):
        """Verify scale names render as escaped text instead of executable script markup."""
        self.create(name='<script>alert(1)</script>')
        html = self.client.get('/rankings').get_data(as_text=True)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)


if __name__ == '__main__':
    unittest.main()
