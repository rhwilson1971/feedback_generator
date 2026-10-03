import unittest
from unittest.mock import patch

from bson import ObjectId
import app as app_module
from ranking_support import Collection


class ReturnContainerTests(unittest.TestCase):
    def setUp(self):
        self.tid, self.cid = ObjectId(), ObjectId()
        self.settings = Collection()
        self.templates = Collection([{'_id': self.tid, 'name': 'Example', 'body': 'Hello',
                                     'placeholders': [], 'container_id': self.cid, 'sort_order': 0}])
        for target, collection in [
            ('app.get_settings_collection', self.settings),
            ('app.get_templates_collection', self.templates),
            ('app.get_containers_collection', Collection([{'_id': self.cid, 'name': 'Essays',
                                                          'category': '', 'sort_order': 0}])),
            ('database.get_ranking_scales_collection', Collection()),
        ]:
            patcher = patch(target, return_value=collection)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def test_enabled_by_default_and_visible_in_settings(self):
        self.assertTrue(app_module.get_settings().get('reopen_container_after_feedback'))
        html = self.client.get('/settings').get_data(as_text=True)
        self.assertIn('name="reopen_container_after_feedback"', html)

    def test_back_link_carries_template_before_and_after_generation(self):
        url = f'/templates/{self.tid}/generate'
        for response in [self.client.get(url), self.client.post(url)]:
            html = response.get_data(as_text=True)
            self.assertIn(f'href="/?return_template={self.tid}"', html)
            self.assertIn('Back to templates', html)

    def test_disabled_preference_removes_return_link_and_restoration(self):
        self.settings.insert_one({'_id': app_module.SETTINGS_DOC_ID,
                                  'reopen_container_after_feedback': False})
        html = self.client.get(f'/templates/{self.tid}/generate').get_data(as_text=True)
        self.assertNotIn('return_template=', html)
        html = self.client.get(f'/?return_template={self.tid}').get_data(as_text=True)
        self.assertNotIn('initReturnContainer(', html)

    def test_enabled_index_initializes_return_behavior(self):
        html = self.client.get(f'/?return_template={self.tid}').get_data(as_text=True)
        self.assertIn('initReturnContainer(', html)

    def test_checkbox_saves_enabled_and_disabled(self):
        self.client.post('/settings', data={'reopen_container_after_feedback': 'on'})
        self.assertTrue(app_module.get_settings().get('reopen_container_after_feedback'))
        self.client.post('/settings', data={})
        self.assertFalse(app_module.get_settings().get('reopen_container_after_feedback'))
