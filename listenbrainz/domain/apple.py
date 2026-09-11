from datetime import datetime, timedelta
from typing import Optional

import jwt
from flask import current_app

from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth
from listenbrainz.domain.external_service import ExternalService
from listenbrainz.webserver import db_conn

DEVELOPER_TOKEN_VALIDITY = timedelta(days=180)


class AppleService(ExternalService):

    def __init__(self):
        super(AppleService, self).__init__(ExternalServiceType.APPLE)
        self.apple_music_key = current_app.config["APPLE_MUSIC_KEY"]
        self.apple_music_kid = current_app.config["APPLE_MUSIC_KID"]
        self.apple_music_team_id = current_app.config["APPLE_MUSIC_TEAM_ID"]

    def fetch_access_token(self):
        """ Generate an Apple Music JWT developer token for use with Apple Music API.
        Returns:
            a dict with the following keys
            {
                'access_token',
                'expires_at',
            }
        """
        iat = datetime.now()
        exp = iat + DEVELOPER_TOKEN_VALIDITY

        iat = int(iat.timestamp())
        exp = int(exp.timestamp())

        token = jwt.encode(
            {"iss": self.apple_music_team_id, "iat": iat, "exp": exp},
            self.apple_music_key,
            "ES256",
            headers={"kid": self.apple_music_kid}
        )
        return {"access_token": token, "expires_at": exp}

    def get_user(self, user_id: int, refresh: bool = False) -> Optional[dict]:
        """ If refresh = True, then check whether the developer token has expired and
        regenerate it before returning the user."""
        user = super().get_user(user_id)
        if user and refresh and self.user_oauth_token_has_expired(user):
            user = self.refresh_access_token(user["user_id"])
        return user

    def refresh_access_token(self, user_id: int) -> dict:
        """ Regenerate the Apple Music developer token for the given user.

        Apple Music does not offer a refresh token flow like Spotify. Instead, the
        developer token (stored as the access token) is a JWT that expires after
        DEVELOPER_TOKEN_VALIDITY and must be regenerated. The user's MusicKit token
        (stored as the refresh token) remains valid and is left unchanged.

        Args:
            user_id (int): the ListenBrainz row ID of the user whose token is to be refreshed

        Returns:
            user (dict): the same user with an updated developer token
        """
        token = self.fetch_access_token()
        external_service_oauth.update_token(
            db_conn, user_id=user_id, service=self.service,
            access_token=token["access_token"], refresh_token=None,
            expires_at=token["expires_at"]
        )
        return self.get_user(user_id)

    def add_new_user(self, user_id: int) -> bool:
        """ Create a new apple music row to store a user specific developer token

        Args:
            user_id: A flask auth `current_user.id`
        """
        token = self.fetch_access_token()
        access_token = token["access_token"]
        # refresh_token = token["music_user_token"]
        expires_at = token["expires_at"]
        external_service_oauth.save_token(
            db_conn=db_conn,
            user_id=user_id, service=self.service, access_token=access_token,
            refresh_token=None, token_expires_ts=expires_at, record_listens=False,
            scopes=[], external_user_id=None
        )
        return True

    def revoke_user(self, user_id: int):
        """ Delete the user's connection to external service but retain
        the last import error message.

        Args:
            user_id (int): the ListenBrainz row ID of the user
        """
        external_service_oauth.delete_token(user_id, self.service, remove_import_log=False)

    def set_token(self, user_id: int, music_user_token: str):
        """ Create a new apple music row to store a user specific developer token

        Args:
            user_id: A flask auth `current_user.id`
            music_user_token: A string containing the user token returned by MusicKit after authorization
        """
        token = self.fetch_access_token()

        access_token = token["access_token"]
        expires_at = token["expires_at"]
        external_service_oauth.update_token(
            db_conn,
            user_id=user_id, service=self.service, access_token=access_token,
            refresh_token=music_user_token, expires_at=expires_at
        )
        return True
