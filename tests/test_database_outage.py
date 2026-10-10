import unittest
from unittest.mock import patch

from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError
import app as app_module


class DatabaseOutageTests(unittest.TestCase):
    """Verify unavailable responses without a running MongoDB server."""

    def test_settings_outage_is_friendly_and_recovers(self):
        """Settings failures render once without exposing exception details."""
        client = app_module.app.test_client()
        with patch.object(app_module, 'get_settings', side_effect=ServerSelectionTimeoutError('secret-host')) as settings:
            response = client.get('/settings')
            self.assertEqual(response.status_code, 503)
            self.assertIn(b"We&#39;ll be right back", response.data)
            self.assertNotIn(b'secret-host', response.data)
            self.assertEqual(settings.call_count, 1)
            self.assertEqual(response.headers['X-Database-Unavailable'], '1')
        with patch.object(app_module, 'get_settings', return_value=app_module.DEFAULT_SETTINGS):
            self.assertEqual(client.get('/settings').status_code, 200)

    def test_write_failure_and_standalone_page(self):
        """Failed background writes and direct outage visits need no settings."""
        client = app_module.app.test_client()
        with patch.object(app_module, 'get_containers_collection', side_effect=AutoReconnect('secret-host')):
            response = client.post('/containers/reorder', json=['012345678901234567890123'])
            self.assertEqual(response.status_code, 503)
            self.assertIn(b'Try again', response.data)
        with patch.object(app_module, 'get_settings', side_effect=AssertionError('must not access database')):
            self.assertEqual(client.get('/unavailable').status_code, 503)

    def test_unrelated_errors_are_not_mislabeled(self):
        """Programming errors retain normal Flask error handling."""
        with patch.object(app_module, 'get_settings', side_effect=ValueError('bug')):
            self.assertEqual(app_module.app.test_client().get('/settings').status_code, 500)
