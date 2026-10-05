"""Verify editor routes opt into the shared unsaved-change guard."""
import unittest
from unittest.mock import patch
from bson import ObjectId
import app as app_module
from ranking_support import Collection


class UnsavedFormIntegrationTests(unittest.TestCase):
    def setUp(self):
        """Provide isolated collections for every editor's render dependencies."""
        self.tid, self.cid, self.sid = ObjectId(), ObjectId(), ObjectId()
        templates = Collection([{'_id': self.tid, 'name': 'Example', 'body': 'Hi {name}',
                                'placeholders': [{'name': 'name', 'input_type': 'freeform', 'options': []}],
                                'container_id': self.cid, 'sort_order': 0}])
        containers = Collection([{'_id': self.cid, 'name': 'Essays', 'category': 'Default', 'sort_order': 0}])
        scales = Collection([{'_id': self.sid, 'name': 'Scale', 'name_key': 'scale',
                             'ranks': [{'id': 1, 'description': 'Good'}]}])
        for target, collection in [
            ('app.get_settings_collection', Collection()),
            ('app.get_templates_collection', templates),
            ('app.get_containers_collection', containers),
            ('database.get_ranking_scales_collection', scales),
            ('database.get_templates_collection', templates),
        ]:
            patcher = patch(target, return_value=collection)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def test_all_editor_routes_opt_in(self):
        """Protect create/edit forms and generation, with helper loaded after setup."""
        for route in ['/templates/new', f'/templates/{self.tid}/edit', '/containers/new',
                      f'/containers/{self.cid}/edit', '/rankings/new', f'/rankings/{self.sid}/edit',
                      '/settings', f'/templates/{self.tid}/generate']:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn('data-unsaved-form', html)
                self.assertIn('/static/unsaved-forms.js', html)
                self.assertGreater(html.index('/static/unsaved-forms.js'), html.index('/static/app.js'))

    def test_generation_ignores_inactive_copy_name(self):
        """Exclude the suggested copy name while Use once is selected."""
        html = self.client.get(f'/templates/{self.tid}/generate').get_data(as_text=True)
        self.assertIn('data-unsaved-ignore-if="#useOnce:checked"', html)
        self.assertGreater(html.index('/static/unsaved-forms.js'), html.index('initCustomFeedback('))

    def test_validation_and_result_pages_keep_guard(self):
        """Redisplayed errors and successful generation retain opt-in markers."""
        responses = [self.client.post('/templates', data={'name': '', 'body': 'Draft'}),
                     self.client.post('/rankings', data={'name': ''}),
                     self.client.post(f'/templates/{self.tid}/generate', data={'body': ''}),
                     self.client.post(f'/templates/{self.tid}/generate', data={'ph_name': 'Ana'})]
        self.assertEqual([r.status_code for r in responses], [400, 400, 400, 200])
        for response in responses:
            self.assertIn('data-unsaved-form', response.get_data(as_text=True))

    def test_list_pages_have_no_protected_forms(self):
        """Keep copy/delete actions and listing filters outside the editor guard."""
        for route in ['/', '/rankings']:
            html = self.client.get(route).get_data(as_text=True)
            self.assertNotIn('data-unsaved-form', html)
