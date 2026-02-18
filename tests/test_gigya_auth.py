"""Tests for Gigya OIDC authentication flow (mocked HTTP)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from cremalink.clients.auth import (
    AuthTokens,
    GigyaAuthError,
    authenticate_gigya,
    _get_query_param,
)


def test_get_query_param():
    url = "https://example.com/callback?code=ABC123&state=xyz"
    assert _get_query_param(url, "code") == "ABC123"
    assert _get_query_param(url, "state") == "xyz"
    assert _get_query_param(url, "missing") is None


def test_get_query_param_empty():
    assert _get_query_param("https://example.com/", "foo") is None


class TestAuthenticateGigya:
    """Tests for the full 8-step Gigya flow with mocked HTTP."""

    def _mock_responses(self):
        """Build a sequence of mock responses for the 8 auth steps."""
        # Step 1: OIDC authorize -> redirect with context
        r1 = MagicMock()
        r1.headers = {"Location": "https://login.example.com?context=test_context_123"}

        # Step 2: getIDs -> ucid, gmid, gmidTicket
        r2 = MagicMock()
        r2.json.return_value = {
            "ucid": "test_ucid",
            "gmid": "test_gmid",
            "gmidTicket": "test_ticket",
        }

        # Step 3: accounts.login -> login_token
        r3 = MagicMock()
        r3.json.return_value = {
            "errorCode": 0,
            "sessionInfo": {"login_token": "test_login_token"},
        }

        # Step 4: getUserInfo -> UID, UIDSignature, signatureTimestamp
        r4 = MagicMock()
        r4.json.return_value = {
            "UID": "test_uid",
            "UIDSignature": "test_uid_sig",
            "signatureTimestamp": "12345",
        }

        # Step 5: consent page -> HTML with signature
        r5 = MagicMock()
        r5.text = "some html const consentObj2Sig = 'test_consent_sig'; more html"

        # Step 6: authorize/continue -> redirect with code
        r6 = MagicMock()
        r6.headers = {"Location": "https://google.it?code=test_auth_code"}

        # Step 7: token exchange -> IDP access_token
        r7 = MagicMock()
        r7.json.return_value = {"access_token": "test_idp_token"}

        # Step 8: Ayla token_sign_in -> access + refresh
        r8 = MagicMock()
        r8.json.return_value = {
            "access_token": "test_ayla_access",
            "refresh_token": "test_ayla_refresh",
        }

        return [r1, r2, r3, r4, r5, r6, r7, r8]

    @patch("cremalink.clients.auth.requests")
    def test_full_flow_success(self, mock_requests):
        responses = self._mock_responses()
        # Map calls: get, get, post, post, get, get, post, post
        mock_requests.get.side_effect = [
            responses[0],  # Step 1
            responses[1],  # Step 2 (json called on return)
            responses[4],  # Step 5
            responses[5],  # Step 6
        ]
        # For steps that chain .json(), the mock should return the mock itself
        mock_requests.get.return_value = MagicMock()

        mock_requests.post.side_effect = [
            responses[2],  # Step 3
            responses[3],  # Step 4
            responses[6],  # Step 7
            responses[7],  # Step 8
        ]

        # Need to mock get to return in sequence
        mock_requests.get = MagicMock(side_effect=[
            responses[0], responses[1], responses[4], responses[5],
        ])
        mock_requests.post = MagicMock(side_effect=[
            responses[2], responses[3], responses[6], responses[7],
        ])

        tokens = authenticate_gigya("test@example.com", "password123")

        assert isinstance(tokens, AuthTokens)
        assert tokens.access_token == "test_ayla_access"
        assert tokens.refresh_token == "test_ayla_refresh"

    @patch("cremalink.clients.auth.requests")
    def test_login_error_raises(self, mock_requests):
        responses = self._mock_responses()
        # Step 3 returns an error
        r3_error = MagicMock()
        r3_error.json.return_value = {
            "errorCode": 403042,
            "errorMessage": "Invalid LoginID",
        }

        mock_requests.get = MagicMock(side_effect=[
            responses[0], responses[1],
        ])
        mock_requests.post = MagicMock(side_effect=[r3_error])

        with pytest.raises(GigyaAuthError, match="Invalid LoginID"):
            authenticate_gigya("bad@example.com", "wrong")

    @patch("cremalink.clients.auth.requests")
    def test_missing_context_raises(self, mock_requests):
        r1_bad = MagicMock()
        r1_bad.headers = {"Location": "https://login.example.com?no_context=true"}

        mock_requests.get = MagicMock(side_effect=[r1_bad])

        with pytest.raises(GigyaAuthError, match="context"):
            authenticate_gigya("test@example.com", "password123")

    @patch("cremalink.clients.auth.requests")
    def test_missing_code_raises(self, mock_requests):
        responses = self._mock_responses()
        # Step 6 missing code in redirect
        r6_bad = MagicMock()
        r6_bad.headers = {"Location": "https://google.it?error=access_denied"}

        mock_requests.get = MagicMock(side_effect=[
            responses[0], responses[1], responses[4], r6_bad,
        ])
        mock_requests.post = MagicMock(side_effect=[
            responses[2], responses[3],
        ])

        with pytest.raises(GigyaAuthError, match="authorization code"):
            authenticate_gigya("test@example.com", "password123")


def test_auth_tokens_dataclass():
    tokens = AuthTokens(access_token="abc", refresh_token="def")
    assert tokens.access_token == "abc"
    assert tokens.refresh_token == "def"
