"""Offline validator for real-Viber E2E config. No network, no Viber calls.

Reads a dotenv file (default: backend/.env) and checks that
VIBER_AUTH_TOKEN / VIBER_WEBHOOK_URL / PUBLIC_BASE_URL are consistent.
Secrets are never printed in full, only masked.

Usage:
    python scripts/check_viber_config.py --env backend/.env
    python scripts/check_viber_config.py --env backend/.env.production
"""

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

PLACEHOLDER_URL_PARTS = ("your-public-host", "your-backend-public", "your-ngrok-host", "example.com", "localhost", "127.0.0.1")


def parse_dotenv(path: Path) -> dict:
    values = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        values[key] = val
    return values


def is_placeholder_token(token: str) -> bool:
    t = token.strip().lower()
    return not t or t in ("test-viber-auth-token", "change-me", "change-me-viber-auth-token") or "change-me" in t


def mask(secret: str) -> str:
    if not secret:
        return "<empty>"
    if len(secret) <= 8:
        return "*** (len=%d)" % len(secret)
    return "%s*** (len=%d)" % (secret[:4], len(secret))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Viber E2E env offline")
    parser.add_argument("--env", default="backend/.env", help="Path to dotenv file")
    args = parser.parse_args()

    env_path = Path(args.env)
    if not env_path.is_file():
        print("FAIL  env file not found: %s" % env_path)
        return 1

    env = parse_dotenv(env_path)
    failures, warnings = [], []

    def check(ok: bool, label: str, detail: str = "", warn_only: bool = False) -> None:
        status = "PASS " if ok else ("WARN " if warn_only else "FAIL ")
        print("%s %s %s" % (status, label, detail))
        if not ok:
            (warnings if warn_only else failures).append(label)

    token = env.get("VIBER_AUTH_TOKEN", "")
    webhook = env.get("VIBER_WEBHOOK_URL", "")
    public_base = env.get("PUBLIC_BASE_URL", "")
    api_base = env.get("VIBER_API_BASE_URL", "https://chatapi.viber.com/pa")
    cors = env.get("CORS_ORIGINS", "")
    debug = env.get("DEBUG", "")
    environment = env.get("ENVIRONMENT", "")
    secret = env.get("SECRET_KEY", "")

    check(not is_placeholder_token(token) and len(token) >= 16,
          "VIBER_AUTH_TOKEN set", "value=%s" % mask(token))
    if token == "test-viber-auth-token":
        print("      hint: test token only works with mock_viber.py, not real Viber")

    parsed = urlparse(webhook)
    check(parsed.scheme == "https", "VIBER_WEBHOOK_URL https", "value=%s" % webhook)
    check(parsed.path == "/api/v1/viber/webhook", "VIBER_WEBHOOK_URL path",
          "got path=%s" % (parsed.path or "<empty>"))
    check(not any(p in webhook for p in PLACEHOLDER_URL_PARTS), "VIBER_WEBHOOK_URL real host",
          "host=%s" % (parsed.hostname or "<empty>"))

    base_parsed = urlparse(public_base)
    if public_base:
        check(base_parsed.scheme == "https", "PUBLIC_BASE_URL https", "value=%s" % public_base)
        check(webhook.startswith(public_base.rstrip("/")), "WEBHOOK under PUBLIC_BASE_URL",
              "webhook=%s base=%s" % (webhook, public_base))
    else:
        check(False, "PUBLIC_BASE_URL set",
              "missing -> attachments default to http://localhost:8000, Viber cannot fetch them")

    check("localhost" not in api_base and "127.0.0.1" not in api_base, "VIBER_API_BASE_URL real",
          "value=%s (mock would be http://localhost:9000/pa)" % api_base)
    check(bool(cors), "CORS_ORIGINS set", "value=%s" % cors, warn_only=True)
    check(secret not in ("", "change-me", "change-me-generate-a-long-random-string") and len(secret) >= 32,
          "SECRET_KEY not default", "value=%s" % mask(secret), warn_only=True)
    if debug.lower() == "true" or environment == "development":
        check(True, "DEBUG/ENVIRONMENT note",
              "DEBUG=%s ENVIRONMENT=%s (fine for local ngrok test)" % (debug, environment),
              warn_only=True)

    print()
    if failures:
        print("RESULT FAILED: %d check(s) failed (%s)" % (len(failures), ", ".join(failures)))
        return 1
    if warnings:
        print("RESULT OK with %d warning(s): %s" % (len(warnings), ", ".join(warnings)))
        return 0
    print("RESULT OK - ready to register webhook")
    return 0


if __name__ == "__main__":
    sys.exit(main())
