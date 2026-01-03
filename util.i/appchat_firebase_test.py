"""
Smoke-test Firebase Realtime Database connectivity using Anonymous Auth.

What it does:
- Signs in anonymously via Identity Toolkit REST API
- Verifies the ID token belongs to the expected Firebase project (optional but recommended)
- Writes a test payload to RTDB
- Reads it back and compares

Run:
  python appchat_firebase_test.py

Notes:
- If you get: 401 {"error":"Permission denied"}
  Most common causes:
    1) API key is from a different Firebase project than the database_url
    2) RTDB rules deny write/read for auth != null
    3) Anonymous auth disabled
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests


@dataclass(frozen=True)
class FirebaseConfig:
    api_key: str
    database_url: str
    expected_project_id: Optional[str] = None  # set to verify token project (recommended)


# ✅ Fill these with values from the SAME Firebase project
FIREBASE = FirebaseConfig(
    api_key="AIzaSyAjUxVqxoRRp7piqzYTZIzlaAV2qQO-ROU",
    database_url="https://raxstock-default-rtdb.firebaseio.com",
    # Optional but strongly recommended: set to your Firebase Project ID (NOT name).
    # In Firebase console: Project settings -> General -> Project ID
    expected_project_id=None,  # e.g. "raxstock"
)

TIMEOUT = 20


def jwt_payload(token: str) -> Dict[str, Any]:
    """Decode JWT payload without verifying signature (good enough for debugging project mismatch)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload_b64 = parts[1]
    # Add padding for base64url decode
    payload_b64 += "=" * (-len(payload_b64) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return {}


def firebase_anonymous_token(cfg: FirebaseConfig) -> str:
    """Return an ID token from Firebase anonymous auth."""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={cfg.api_key}"
    resp = requests.post(url, json={}, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("idToken")
    if not token:
        raise RuntimeError(f"Missing idToken in response: {data}")
    return token


def assert_token_project(cfg: FirebaseConfig, token: str) -> None:
    """
    Verify the token appears to be issued for the expected Firebase project.
    This catches the common 'API key + DB URL belong to different projects' issue.
    """
    if not cfg.expected_project_id:
        return

    payload = jwt_payload(token)
    aud = payload.get("aud")  # typically the project id
    iss = payload.get("iss")  # typically https://securetoken.google.com/<project_id>

    if aud != cfg.expected_project_id or (isinstance(iss, str) and not iss.endswith("/" + cfg.expected_project_id)):
        raise RuntimeError(
            "Token project mismatch.\n"
            f"- expected_project_id: {cfg.expected_project_id}\n"
            f"- token.aud: {aud}\n"
            f"- token.iss: {iss}\n\n"
            "Fix:\n"
            "  Use the Web API Key from the same Firebase project that owns the RTDB instance:\n"
            "  Firebase Console -> Project settings -> General -> Web API Key\n"
        )


def rtdb_write(cfg: FirebaseConfig, id_token: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{cfg.database_url}/{path}.json"
    resp = requests.put(url, params={"auth": id_token}, json=payload, timeout=TIMEOUT)
    if not resp.ok:
        raise RuntimeError(f"RTDB write failed [{resp.status_code}]: {resp.text}")
    return resp.json()


def rtdb_get(cfg: FirebaseConfig, id_token: str, path: str) -> Optional[Dict[str, Any]]:
    url = f"{cfg.database_url}/{path}.json"
    resp = requests.get(url, params={"auth": id_token}, timeout=TIMEOUT)
    if not resp.ok:
        raise RuntimeError(f"RTDB read failed [{resp.status_code}]: {resp.text}")
    return resp.json()


def main() -> None:
    print("Signing in anonymously...")
    token = firebase_anonymous_token(FIREBASE)

    payload = jwt_payload(token)
    print("Got ID token (truncated):", token[:12] + "...")
    if payload:
        print("Token debug:")
        print("  aud:", payload.get("aud"))
        print("  iss:", payload.get("iss"))
        print("  user_id:", payload.get("user_id"))

    # Optional but helpful: fail fast if your API key isn't from the same project as the DB
    assert_token_project(FIREBASE, token)

    ts = int(time.time())
    test_path = f"threads/test/messages/test_message_{ts}"
    test_payload = {"message": "Hello from appchat_firebase_test.py", "sent_at": ts}


    print(f"Writing to {test_path} ...")
    try:
        write_result = rtdb_write(FIREBASE, token, test_path, test_payload)
        print("Write result:", json.dumps(write_result, indent=2))
    except Exception as err:
        print("\nRTDB write error:", err)
        print(
            "\nLikely causes:\n"
            "1) API key and database_url belong to different Firebase projects (MOST COMMON)\n"
            "2) Anonymous Auth is not enabled (Firebase Console -> Auth -> Sign-in method)\n"
            "3) RTDB Rules deny writes/reads\n\n"
            "Quick RTDB rules for smoke test (TEMPORARY):\n"
            '{ "rules": { ".read": "auth != null", ".write": "auth != null" } }\n\n'
            "Also verify you are editing rules for THIS database:\n"
            f"  {FIREBASE.database_url}\n"
        )
        return

    print("Reading back...")
    try:
        read_back = rtdb_get(FIREBASE, token, test_path)
        print("Read result:", json.dumps(read_back, indent=2))
    except Exception as err:
        print("\nRTDB read error:", err)
        return

    if read_back == test_payload:
        print("✅ Firebase RTDB connectivity looks good.")
    else:
        print("⚠️ Data mismatch. Read back differs from what was written:")
        print("Expected:", json.dumps(test_payload, indent=2))
        print("Got     :", json.dumps(read_back, indent=2))


if __name__ == "__main__":
    main()
