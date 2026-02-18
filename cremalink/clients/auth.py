"""
Gigya OIDC authentication flow for De'Longhi cloud services.

Implements the full 8-step authentication process: Gigya OIDC authorize,
session IDs, account login, user info, consent, authorization code exchange,
IDP token, and finally Ayla access token retrieval.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

from cremalink.resources import load_api_config


class GigyaAuthError(Exception):
    """Raised when any step of the Gigya OIDC authentication flow fails."""
    pass


@dataclass
class AuthTokens:
    """
    Access and refresh tokens obtained from the Ayla cloud.

    Attributes:
        access_token: The short-lived access token for API requests.
        refresh_token: The long-lived refresh token for obtaining new access tokens.
    """
    access_token: str
    refresh_token: str


_BROWSER_UA = "DeLonghiComfort/5.1.1"
_GIGYA_BASE = "https://fidm.eu1.gigya.com"
_SOCIALIZE_BASE = "https://socialize.eu1.gigya.com"
_ACCOUNTS_BASE = "https://accounts.eu1.gigya.com"
_CONSENT_BASE = "https://aylaopenid.delonghigroup.com"
_REDIRECT_URI = "https://google.it"
_SCOPE = "openid email profile UID comfort en alexa"


def _get_query_param(url: str, param: str) -> str | None:
    """Extract a single query parameter from a URL."""
    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    values = parsed.get(param)
    return values[0] if values else None


def authenticate_gigya(email: str, password: str) -> AuthTokens:
    """
    Perform the full Gigya OIDC -> Ayla token authentication flow.

    This is an 8-step process that authenticates against De'Longhi's Gigya
    identity provider and exchanges the resulting token for Ayla cloud
    credentials.

    Args:
        email: The De'Longhi account email address.
        password: The De'Longhi account password.

    Returns:
        An ``AuthTokens`` instance with access and refresh tokens.

    Raises:
        GigyaAuthError: If any step of the authentication flow fails.
    """
    conf = load_api_config()
    gigya = conf["GIGYA"]
    ayla = conf["AYLA"]

    api_key = gigya["API_KEY"]
    client_id = gigya["CLIENT_ID"]
    client_secret = gigya["CLIENT_SECRET"]
    sdk_build = gigya.get("SDK_BUILD", "16650")
    app_id = ayla["APP_ID"]
    app_secret = ayla["APP_SECRET"]
    oauth_url = ayla["OAUTH_URL"]

    headers = {"User-Agent": _BROWSER_UA}

    # Step 1: Initiate OIDC authorize
    try:
        r = requests.get(
            f"{_GIGYA_BASE}/oidc/op/v1.0/{api_key}/authorize",
            headers=headers,
            params={
                "client_id": client_id,
                "response_type": "code",
                "redirect_uri": _REDIRECT_URI,
                "scope": _SCOPE,
                "nonce": str(int(datetime.now().timestamp())),
            },
            allow_redirects=False,
        )
        location = r.headers.get("Location", "")
        context = _get_query_param(location, "context")
        if not context:
            raise GigyaAuthError("Failed to get OIDC context from authorize redirect.")
    except GigyaAuthError:
        raise
    except Exception as e:
        raise GigyaAuthError(f"OIDC authorize failed: {e}") from e

    # Step 2: Get Gigya session IDs
    try:
        r = requests.get(
            f"{_SOCIALIZE_BASE}/socialize.getIDs",
            headers=headers,
            params={
                "APIKey": api_key,
                "includeTicket": True,
                "pageURL": f"{_CONSENT_BASE}/",
                "sdk": "js_latest",
                "sdkBuild": sdk_build,
                "format": "json",
            },
        ).json()
        ucid = r["ucid"]
        gmid = r["gmid"]
        gmid_ticket = r["gmidTicket"]
    except KeyError as e:
        raise GigyaAuthError(f"Failed to get session IDs: missing {e}") from e
    except Exception as e:
        raise GigyaAuthError(f"Session ID retrieval failed: {e}") from e

    # Step 3: Account login
    try:
        r = requests.post(
            f"{_ACCOUNTS_BASE}/accounts.login",
            headers=headers,
            data={
                "loginID": email,
                "password": password,
                "sessionExpiration": 7884009,
                "targetEnv": "jssdk",
                "include": "profile,data,emails,subscriptions,preferences",
                "includeUserInfo": True,
                "loginMode": "standard",
                "APIKey": api_key,
                "source": "showScreenSet",
                "sdk": "js_latest",
                "authMode": "cookie",
                "pageURL": f"{_CONSENT_BASE}/",
                "gmid": gmid,
                "ucid": ucid,
                "sdkBuild": sdk_build,
                "format": "json",
            },
        ).json()
        if r.get("errorCode", 0) != 0:
            raise GigyaAuthError(f"Login failed: {r.get('errorMessage', 'Unknown error')}")
        login_token = r["sessionInfo"]["login_token"]
    except GigyaAuthError:
        raise
    except KeyError as e:
        raise GigyaAuthError(f"Login response missing field: {e}") from e
    except Exception as e:
        raise GigyaAuthError(f"Account login failed: {e}") from e

    # Step 4: Get user info
    try:
        r = requests.post(
            f"{_SOCIALIZE_BASE}/socialize.getUserInfo",
            headers=headers,
            data={
                "enabledProviders": "*",
                "APIKey": api_key,
                "sdk": "js_latest",
                "login_token": login_token,
                "authMode": "cookie",
                "pageURL": f"{_CONSENT_BASE}/",
                "gmid": gmid,
                "ucid": ucid,
                "sdkBuild": sdk_build,
                "format": "json",
            },
        ).json()
        uid = r["UID"]
        uid_sig = r["UIDSignature"]
        sig_ts = r["signatureTimestamp"]
    except KeyError as e:
        raise GigyaAuthError(f"User info missing field: {e}") from e
    except Exception as e:
        raise GigyaAuthError(f"User info retrieval failed: {e}") from e

    # Step 5: Get consent signature
    try:
        r = requests.get(
            f"{_CONSENT_BASE}/OIDCConsentPage.php",
            headers=headers,
            params={
                "context": context,
                "clientID": client_id,
                "scope": "openid+email+profile+UID+comfort+en+alexa",
                "UID": uid,
                "UIDSignature": uid_sig,
                "signatureTimestamp": sig_ts,
            },
        ).text
        signature = r.split("const consentObj2Sig = '")[1].split("';")[0]
    except (IndexError, ValueError) as e:
        raise GigyaAuthError(f"Failed to extract consent signature: {e}") from e
    except Exception as e:
        raise GigyaAuthError(f"Consent page retrieval failed: {e}") from e

    # Step 6: Complete authorization
    try:
        r = requests.get(
            f"{_GIGYA_BASE}/oidc/op/v1.0/{api_key}/authorize/continue",
            headers=headers,
            params={
                "context": context,
                "login_token": login_token,
                "consent": json.dumps(
                    {
                        "scope": _SCOPE,
                        "clientID": client_id,
                        "context": context,
                        "UID": uid,
                        "consent": True,
                    },
                    separators=(",", ":"),
                ),
                "sig": signature,
                "gmidTicket": gmid_ticket,
            },
            allow_redirects=False,
        )
        location = r.headers.get("Location", "")
        code = _get_query_param(location, "code")
        if not code:
            raise GigyaAuthError("Failed to get authorization code from redirect.")
    except GigyaAuthError:
        raise
    except Exception as e:
        raise GigyaAuthError(f"Authorization continuation failed: {e}") from e

    # Step 7: Exchange code for IDP token
    import base64
    auth_header = "Basic " + base64.b64encode(
        f"{client_id}:{client_secret}".encode()
    ).decode()

    try:
        r = requests.post(
            f"{_GIGYA_BASE}/oidc/op/v1.0/{api_key}/token",
            headers={
                "User-Agent": _BROWSER_UA,
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": _REDIRECT_URI,
            },
        ).json()
        idp_token = r["access_token"]
    except KeyError as e:
        raise GigyaAuthError(f"Token exchange missing field: {e}") from e
    except Exception as e:
        raise GigyaAuthError(f"Token exchange failed: {e}") from e

    # Step 8: Get Ayla access token
    try:
        r = requests.post(
            f"{oauth_url}/api/v1/token_sign_in",
            headers=headers,
            data={
                "app_id": app_id,
                "app_secret": app_secret,
                "token": idp_token,
            },
        ).json()
        return AuthTokens(
            access_token=r["access_token"],
            refresh_token=r.get("refresh_token", ""),
        )
    except KeyError as e:
        raise GigyaAuthError(f"Ayla token response missing field: {e}") from e
    except Exception as e:
        raise GigyaAuthError(f"Ayla token sign-in failed: {e}") from e
