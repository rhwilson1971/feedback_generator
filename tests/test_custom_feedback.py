import unittest
from copy import deepcopy
from unittest.mock import patch

from bson import ObjectId
import app as app_module
from ranking_support import Collection
from test_placeholder_mru import make_tpl


class CustomFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.source = make_tpl(ObjectId(), 'Hi {name}, {grade}', dropdown=('grade',))
        self.source.update(tags=['praise'], ranking_scale_id=ObjectId(), ranking_rank_id=3, sort_order=4)
        self.collection = Collection([self.source])
        for name, value in [('get_templates_collection', self.collection),
                            ('get_settings_collection', Collection())]:
            p = patch.object(app_module, name, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        app_module._placeholder_mru.clear()
        self.client = app_module.app.test_client()
        self.url = f"/templates/{self.source['_id']}/generate"

    def post(self, **data):
        return self.client.post(self.url, data=data)

    def test_one_off_uses_edited_body_and_preserves_draft(self):
        before = deepcopy(self.collection.docs)
        response = self.post(body='Well done {name}!\nKeep going.', ph_name='Ana')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-feedback-generated>Well done Ana!\nKeep going.<', html)
        self.assertIn('>Well done {name}!\nKeep going.</textarea>', html)
        self.assertIn('value="Ana"', html)
        self.assertEqual(self.collection.docs, before)

    def test_saving_keeps_tokens_and_inherits_metadata(self):
        response = self.post(body='{grade}, {new}! {grade}', ph_grade='Great', ph_new='Ana',
                             save_mode='save', new_template_name='Custom praise')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.collection.docs), 2)
        saved = self.collection.docs[-1]
        self.assertEqual(saved['body'], '{grade}, {new}! {grade}')
        self.assertEqual(saved['name'], 'Custom praise')
        for key in ['container_id', 'tags', 'ranking_scale_id', 'ranking_rank_id']:
            self.assertEqual(saved[key], self.source[key])
        self.assertEqual([p['name'] for p in saved['placeholders']], ['grade', 'new'])
        self.assertEqual(saved['placeholders'][0]['options'], ['Good', 'Great'])
        self.assertEqual(saved['placeholders'][1]['input_type'], 'freeform')
        self.assertEqual(saved['sort_order'], 5)
        self.assertIn('created_at', saved)
        self.assertEqual(self.collection.docs[0], self.source)
        html = response.get_data(as_text=True)
        self.assertIn(f'/templates/{saved["_id"]}/generate', html)
        self.assertIn('value="once" checked', html)

    def test_invalid_submissions_do_not_save_and_keep_draft(self):
        for override in [dict(body='  '), dict(ph_name='  '), dict(new_template_name=' '),
                         dict(save_mode='unknown')]:
            with self.subTest(override=override):
                data = dict(body='Edited {name}', ph_name='Ana', save_mode='save', new_template_name='Custom')
                data.update(override)
                response = self.post(**data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(len(self.collection.docs), 1)
                html = response.get_data(as_text=True)
                self.assertIn('role="alert"', html)
                self.assertIn(data['body'] + '</textarea>', html)
                self.assertNotIn('data-feedback-generated', html)

    def test_new_placeholder_values_are_required(self):
        response = self.post(body='{new}', save_mode='once')
        self.assertEqual(response.status_code, 400)
        self.assertIn('name="ph_new"', response.get_data(as_text=True))

    def test_substitution_does_not_replace_tokens_inside_values(self):
        html = self.post(body='{name} {grade}', ph_name='{grade}', ph_grade='Great').get_data(as_text=True)
        self.assertIn('data-feedback-generated>{grade} Great<', html)

    def test_legacy_submission_uses_saved_body(self):
        html = self.post(ph_name='Ana', ph_grade='Good').get_data(as_text=True)
        self.assertIn('data-feedback-generated>Hi Ana, Good<', html)

    def test_body_without_placeholders_can_generate(self):
        html = self.post(body='Plain custom feedback').get_data(as_text=True)
        self.assertIn('data-feedback-generated>Plain custom feedback<', html)

    def test_unicode_and_repeated_placeholder(self):
        html = self.post(body='{élève} {élève}', **{'ph_élève': 'Ana'}).get_data(as_text=True)
        self.assertIn('data-feedback-generated>Ana Ana<', html)

    def test_html_is_escaped(self):
        html = self.post(body='<script>{name}</script>', ph_name='<b>Ana</b>').get_data(as_text=True)
        self.assertIn('&lt;script&gt;&lt;b&gt;Ana&lt;/b&gt;&lt;/script&gt;', html)
