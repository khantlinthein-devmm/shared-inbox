"""Automated smoke test for the Shared Inbox API.

Exercises the full flow without a real Viber token:
login -> RBAC -> Viber webhook -> conversation -> note -> reply -> attachment
-> assignment/status -> filters.

Prerequisites:
    - PostgreSQL up, tables created (`python init_db.py`) and an admin
      bootstrapped (`python create_admin.py --email ...`).
      Override login with SMOKE_ADMIN_EMAIL / SMOKE_ADMIN_PASSWORD.
    - backend running with a mock Viber API, e.g.:
        VIBER_API_BASE_URL=http://localhost:9000/pa uvicorn app.main:app --port 8000
        python mock_viber.py 9000

Usage:
    python smoke_test.py
    API_URL=http://localhost:8000 SMOKE_VIBER_TOKEN=test-viber-auth-token python smoke_test.py
"""

import argparse
import hashlib
import hmac
import json
import os
import random
import sys
import uuid

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000")
VIBER_TOKEN = os.environ.get("SMOKE_VIBER_TOKEN", "test-viber-auth-token")
SMOKE_ADMIN_EMAIL = os.environ.get("SMOKE_ADMIN_EMAIL", os.environ.get("ADMIN_EMAIL", "admin@example.com"))
SMOKE_ADMIN_PASSWORD = os.environ.get("SMOKE_ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "admin123"))

failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    """Record a PASS/FAIL result for the summary at the end."""
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        failures.append(label)


def viber_signature(body: bytes) -> str:
    """HMAC-SHA256 of the raw body keyed with the bot auth token."""
    return hmac.new(VIBER_TOKEN.encode("utf-8"), body, hashlib.sha256).hexdigest()


def make_webhook_payload(contact_id: str, text: str) -> bytes:
    """A minimal Viber `message` callback with unique contact/token."""
    payload = {
        "event": "message",
        "timestamp": 1700000000,
        "message_token": random.randint(100000, 999999999),
        "sender": {
            "id": contact_id,
            "name": "Smoke Tester",
            "avatar": "http://mock/avatar.png",
            "country": "IL",
            "language": "en",
            "api_version": 1,
        },
        "message": {"type": "text", "text": text, "tracking_data": "smoke"},
    }
    return json.dumps(payload).encode("utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test the Shared Inbox API")
    parser.add_argument("--url", default=API_URL, help="Base URL of the backend")
    args = parser.parse_args()
    base = args.url.rstrip("/")

    # Unique identifiers so repeated runs never collide (contact_user_id +
    # channel and channel_message_id are unique).
    contact_id = f"smoke-{uuid.uuid4()}"
    print(f"Target: {base}")
    print(f"Contact: {contact_id}\n")

    async with httpx.AsyncClient(base_url=base, timeout=15.0) as client:
        # 1. Health
        r = await client.get("/")
        check(r.status_code == 200, "GET / (health)", f"-> {r.status_code}")

        # 2. Login (admin bootstrapped via create_admin.py)
        r = await client.post("/api/v1/auth/login", json={"email": SMOKE_ADMIN_EMAIL, "password": SMOKE_ADMIN_PASSWORD})
        check(r.status_code == 200, "POST /auth/login (admin)", f"-> {r.status_code}")
        token = r.json().get("access_token", "") if r.status_code == 200 else ""
        check(bool(token), "login returns access_token")

        # 3. Login with a wrong password is rejected
        r = await client.post("/api/v1/auth/login", json={"email": SMOKE_ADMIN_EMAIL, "password": "wrong"})
        check(r.status_code == 401, "POST /auth/login wrong password -> 401", f"-> {r.status_code}")

        headers = {"Authorization": f"Bearer {token}"}

        # 4. Authenticated identity
        r = await client.get("/api/v1/auth/me", headers=headers)
        check(r.status_code == 200 and r.json().get("role") == "admin", "GET /auth/me (RBAC admin)", f"-> {r.status_code}")

        # 5. Agents list (assignment dropdown source)
        r = await client.get("/api/v1/users/agents", headers=headers)
        agents = r.json() if r.status_code == 200 else []
        check(r.status_code == 200 and any(a.get("role") == "agent" for a in agents), "GET /users/agents", f"-> {r.status_code}")

        # 6. Viber webhook -> creates conversation + inbound message (+ auto-reply)
        body = make_webhook_payload(contact_id, "Hello! I need help with my order.")
        r = await client.post(
            "/api/v1/viber/webhook",
            content=body,
            headers={"X-Viber-Content-Signature": viber_signature(body)},
        )
        check(r.status_code == 200, "POST /viber/webhook", f"-> {r.status_code}")
        check(r.json().get("status") == 0, "webhook ack status=0")

        # 7. Wrong signature is rejected
        r = await client.post(
            "/api/v1/viber/webhook",
            content=body,
            headers={"X-Viber-Content-Signature": "deadbeef"},
        )
        check(r.status_code == 400, "webhook bad signature -> 400", f"-> {r.status_code}")

        # 8. Unassigned filter lists the fresh conversation
        r = await client.get("/api/v1/conversations?status=unassigned", headers=headers)
        convs = r.json() if r.status_code == 200 else []
        conv = next((c for c in convs if c.get("contact_user_id") == contact_id), None)
        check(conv is not None, "GET /conversations?status=unassigned finds contact", f"-> {r.status_code}")
        if conv is None:
            print("  ABORTED (conversation not created)")
            sys.exit(1)
        conv_id = conv["id"]

        # 9. Status filter is actually applied (other statuses excluded)
        r = await client.get("/api/v1/conversations?status=open", headers=headers)
        check(all(c.get("status") == "open" for c in (r.json() if r.status_code == 200 else [])), "status filter returns only matching rows")

        # 10. Conversation detail: inbound message present + sender_name
        r = await client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
        detail = r.json() if r.status_code == 200 else {}
        inbound = [m for m in detail.get("messages", []) if m.get("sender") == "contact"]
        check(r.status_code == 200 and inbound, "GET /conversations/{id} has inbound message", f"-> {r.status_code}")

        # 11. Internal note (now broadcast over WS)
        r = await client.post(
            f"/api/v1/conversations/{conv_id}/notes",
            headers=headers,
            json={"content": "Priority billing issue - follow up by EOD."},
        )
        check(r.status_code == 201, "POST notes -> 201", f"-> {r.status_code}")

        # 12. Agent text reply (sent through mock Viber)
        r = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers,
            json={"text": "Thanks for reaching out - an agent will assist shortly."},
        )
        msg = r.json() if r.status_code == 201 else {}
        check(r.status_code == 201 and msg.get("sender") == "agent", "POST messages (agent reply)", f"-> {r.status_code}")
        check(msg.get("status") == "sent", "reply stored as sent", f"-> {msg.get('status')}")

        # 13. Attachment upload (file mirrored to mock Viber, served under /uploads)
        file_body = b"hello attachment content" * 100
        r = await client.post(
            f"/api/v1/conversations/{conv_id}/attachments",
            headers=headers,
            files={"file": ("report.pdf", file_body, "application/pdf")},
        )
        att = r.json() if r.status_code == 201 else {}
        media_url = att.get("media_url", "")
        check(r.status_code == 201 and "/uploads/" in media_url, "POST attachments -> stored media_url", f"-> {r.status_code}")
        if media_url:
            rr = await client.get(media_url.replace(base, "", 1) if media_url.startswith(base) else media_url)
            check(rr.status_code == 200 and rr.content == file_body, "GET /uploads/{file} serves the file", f"-> {rr.status_code}")

        # 14. Assign + change status (broadcast via WS)
        agent_id = next((a.get("id") for a in agents if a.get("role") == "agent"), None)
        r = await client.patch(
            f"/api/v1/conversations/{conv_id}",
            headers=headers,
            json={"assigned_to_id": agent_id, "status": "open"},
        )
        updated = r.json() if r.status_code == 200 else {}
        check(
            r.status_code == 200 and updated.get("assigned_to_id") == agent_id and updated.get("status") == "open",
            "PATCH conversation (assign + status)",
            f"-> {r.status_code} {updated}",
        )

        # 15. Filters reflect the status change
        r = await client.get(f"/api/v1/conversations?status=open&search=Smoke", headers=headers)
        convs = r.json() if r.status_code == 200 else []
        check(any(c.get("id") == conv_id for c in convs), "open filter + search finds updated conversation")

        # 16. RBAC: unauthenticated / unprivileged calls
        r = await client.get("/api/v1/conversations")
        check(r.status_code == 401, "unauthenticated access -> 401", f"-> {r.status_code}")

        print()
        if failures:
            print(f"SMOKE TEST FAILED: {len(failures)} check(s) failed")
            for f in failures:
                print(f"  - {f}")
            sys.exit(1)
        print("SMOKE TEST PASSED - all checks green")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())