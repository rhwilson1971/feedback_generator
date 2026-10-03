import unittest
from unittest.mock import patch

from bson import ObjectId

import app as app_module
from ranking_support import Collection


class TemplateRankingTests(unittest.TestCase):
    def setUp(self):
        """Stub a shared scale, a legacy template, its container, and settings for route tests."""
        self.sid, self.cid, self.tid = ObjectId(), ObjectId(), ObjectId()
        self.scales = Collection([{'_id': self.sid, 'name': 'Completion', 'name_key': 'completion',
                                   'ranks': [{'id': 1, 'description': 'Completed'},
                                             {'id': 3, 'description': 'Needs work'}]}])
        self.templates = Collection([{'_id': self.tid, 'name': 'Old', 'body': 'Hi {name}',
                                     'placeholders': [{'name': 'name', 'input_type': 'freeform', 'options': []}],
                                     'sort_order': 0, 'container_id': self.cid, 'tags': ['praise']}])
        self.containers = Collection([{'_id': self.cid, 'name': 'Essays', 'sort_order': 0, 'category': 'W'}])
        for target, coll in [('database.get_ranking_scales_collection', self.scales),
                             ('database.get_templates_collection', self.templates),
                             ('app.get_templates_collection', self.templates),
                             ('app.get_containers_collection', self.containers),
                             ('app.get_settings_collection', Collection())]:
            p = patch(target, return_value=coll)
            p.start()
            self.addCleanup(p.stop)
        self.client = app_module.app.test_client()

    def form(self, **extra):
        """Build a ranked template submission with optional field overrides."""
        return {'name': 'New', 'body': 'Hi {name}', 'tags': 'praise', 'container_id': str(self.cid),
                'ranking_scale_id': str(self.sid), 'ranking_rank_id': '1', **extra}

    def test_create_saves_valid_scale_and_rank(self):
        """Verify template creation stores the selected scale ObjectId and integer rank."""
        self.assertEqual(self.client.post('/templates', data=self.form()).status_code, 302)
        template = self.templates.find_one({'name': 'New'})
        self.assertEqual(template.get('ranking_scale_id'), self.sid)
        self.assertEqual(template.get('ranking_rank_id'), 1)

    def test_update_can_rank_and_then_unrank(self):
        """Verify clearing the scale clears both saved references even when a rank is submitted."""
        url = f'/templates/{self.tid}/update'
        self.client.post(url, data=self.form())
        self.assertEqual(self.templates.find_one({'_id': self.tid}).get('ranking_rank_id'), 1)
        self.client.post(url, data=self.form(ranking_scale_id='', ranking_rank_id='3'))
        template = self.templates.find_one({'_id': self.tid})
        self.assertIsNone(template.get('ranking_scale_id'))
        self.assertIsNone(template.get('ranking_rank_id'))

    def test_unranked_create_and_legacy_edit_need_no_migration(self):
        """Verify omitted ranking fields and legacy templates remain valid and editable."""
        data = self.form()
        data.pop('ranking_scale_id')
        data.pop('ranking_rank_id')
        self.assertEqual(self.client.post('/templates', data=data).status_code, 302)
        self.assertIsNone(self.templates.find_one({'name': 'New'}).get('ranking_scale_id'))
        html = self.client.get(f'/templates/{self.tid}/edit').get_data(as_text=True)
        self.assertIn('Unranked', html)
        self.assertIn('id="rankingScale"', html)
        self.assertIn('Hi {name}', html)

    def test_invalid_reference_preserves_input_and_does_not_save(self):
        """Verify invalid scale or rank references preserve submitted text without creating a template."""
        for extra in [dict(ranking_scale_id='bad'), dict(ranking_scale_id=str(ObjectId())),
                      dict(ranking_rank_id=''), dict(ranking_rank_id='2'), dict(ranking_rank_id='x')]:
            response = self.client.post('/templates', data=self.form(name='Keep me', body='Keep {name}', **extra))
            self.assertEqual(response.status_code, 400)
            html = response.get_data(as_text=True)
            self.assertIn('value="Keep me"', html)
            self.assertIn('Keep {name}', html)
        self.assertEqual(self.templates.count_documents({}), 1)

    def test_invalid_update_leaves_original_unchanged(self):
        """Verify an invalid rank rejects an update without changing the stored template name."""
        response = self.client.post(f'/templates/{self.tid}/update', data=self.form(ranking_rank_id='999'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.templates.find_one({'_id': self.tid})['name'], 'Old')

    def test_copy_template_preserves_shared_references(self):
        """Verify a template copy retains its ranking references without duplicating the scale."""
        self.templates.update_one({'_id': self.tid}, {'$set': {'ranking_scale_id': self.sid, 'ranking_rank_id': 3}})
        self.client.post(f'/templates/{self.tid}/copy', data={'container_id': ''})
        copy = self.templates.find_one({'container_id': None})
        self.assertEqual(copy.get('ranking_scale_id'), self.sid)
        self.assertEqual(copy.get('ranking_rank_id'), 3)
        self.assertEqual(self.scales.count_documents({}), 1)

    def test_copy_container_preserves_shared_references(self):
        """Verify templates copied with a container keep their scale and rank references."""
        self.templates.update_one({'_id': self.tid}, {'$set': {'ranking_scale_id': self.sid, 'ranking_rank_id': 1}})
        self.client.post(f'/containers/{self.cid}/copy', data={'name': 'Copy'})
        new_cid = self.containers.find_one({'name': 'Copy'})['_id']
        copy = self.templates.find_one({'container_id': new_cid})
        self.assertEqual(copy.get('ranking_scale_id'), self.sid)
        self.assertEqual(copy.get('ranking_rank_id'), 1)

    def test_home_badge_resolves_shared_labels_and_filters(self):
        """Verify list metadata and badges use shared references and reflect updated labels."""
        self.templates.update_one({'_id': self.tid}, {'$set': {'ranking_scale_id': self.sid, 'ranking_rank_id': 1}})
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('Completion · 1 — Completed', html)
        self.assertIn(f'data-ranking-scale="{self.sid}"', html)
        self.assertIn('data-ranking-rank="1"', html)
        self.assertIn('id="rankingFilter"', html)
        self.assertIn('id="rankFilter"', html)
        self.scales.update_one({'_id': self.sid}, {'$set': {'name': 'Quality', 'name_key': 'quality',
                                    'ranks': [{'id': 1, 'description': 'Excellent'}]}})
        self.assertIn('Quality · 1 — Excellent', self.client.get('/').get_data(as_text=True))

    def test_unranked_template_has_empty_filter_metadata(self):
        """Verify legacy templates expose empty scale and rank attributes for filtering."""
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('data-ranking-scale=""', html)
        self.assertIn('data-ranking-rank=""', html)

    def test_edit_form_restores_assigned_rank(self):
        """Verify the edit form preselects the saved scale and rank."""
        self.templates.update_one({'_id': self.tid}, {'$set': {'ranking_scale_id': self.sid, 'ranking_rank_id': 3}})
        html = self.client.get(f'/templates/{self.tid}/edit').get_data(as_text=True)
        self.assertIn(f'value="{self.sid}" selected', html)
        self.assertIn('value="3" selected', html)


if __name__ == '__main__':
    unittest.main()
