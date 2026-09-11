from unittest import mock

import listenbrainz.db.user as db_user
from listenbrainz.domain.apple import AppleService

from listenbrainz.tests.integration import NonAPIIntegrationTestCase


class AppleServiceTestCase(NonAPIIntegrationTestCase):

    def setUp(self):
        super(AppleServiceTestCase, self).setUp()
        self.user_id = db_user.create(self.db_conn, 212, 'apple_user')
        self.service = AppleService()
        self.service.add_new_user(self.user_id)
        self.service.set_token(self.user_id, 'music-user-token')

    def test_get_user(self):
        user = self.service.get_user(self.user_id)
        self.assertEqual(user['user_id'], self.user_id)
        self.assertEqual(user['musicbrainz_id'], 'apple_user')
        self.assertEqual(user['refresh_token'], 'music-user-token')
        self.assertIsNotNone(user['access_token'])
        self.assertIsNotNone(user['token_expires'])

    @mock.patch('listenbrainz.domain.apple.AppleService.fetch_access_token')
    def test_refresh_access_token(self, mock_fetch_access_token):
        mock_fetch_access_token.return_value = {
            'access_token': 'new-developer-token',
            'expires_at': 9999999999,
        }

        user = self.service.refresh_access_token(self.user_id)

        self.assertEqual(user['user_id'], self.user_id)
        self.assertEqual(user['access_token'], 'new-developer-token')
        self.assertEqual(user['refresh_token'], 'music-user-token')
        mock_fetch_access_token.assert_called_once_with()

    @mock.patch('listenbrainz.domain.apple.AppleService.fetch_access_token')
    @mock.patch.object(AppleService, 'user_oauth_token_has_expired', return_value=True)
    def test_get_user_with_refresh(self, mock_has_expired, mock_fetch_access_token):
        mock_fetch_access_token.return_value = {
            'access_token': 'new-developer-token',
            'expires_at': 9999999999,
        }

        user = self.service.get_user(self.user_id, refresh=True)

        self.assertEqual(user['access_token'], 'new-developer-token')
        self.assertEqual(user['refresh_token'], 'music-user-token')
        mock_has_expired.assert_called_once()

    def test_get_user_with_refresh_not_expired(self):
        user = self.service.get_user(self.user_id, refresh=True)
        original_access_token = self.service.get_user(self.user_id)['access_token']
        self.assertEqual(user['access_token'], original_access_token)
