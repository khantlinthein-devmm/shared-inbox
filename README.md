# Shared Inbox — Multi-Agent Omni-Channel Customer Support Dashboard

A production-ready skeleton for a shared inbox that lets support agents handle
conversations from multiple messaging channels, in one dashboard, in real time.

- **Backend**: FastAPI, Async WebSockets, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL, JWT auth + RBAC
- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Zustand, WebSockets, Lucide icons
- **Messaging**: channel-agnostic `ChannelClient` interface (`backend/app/services/channels/`)
  with two channels wired up today — **Viber** (webhook ingest + REST client, HMAC signature
  verification) and **Telegram** (Bot API webhook + client, secret-token verification).
  Adding a new channel means one client implementation + one webhook endpoint; the
  conversation/message model, dashboard, and WebSocket feed are shared across all channels.

## Project structure

```
shared-inbox/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry: CORS, routers, WS mount
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic settings (.env)
│   │   │   ├── database.py            # Async engine, session factory
│   │   │   ├── security.py            # bcrypt + JWT helpers
│   │   │   └── deps.py                # get_current_user, require_roles (RBAC)
│   │   ├── models/                    # SQLAlchemy ORM: User, Conversation,
│   │   │                              #   Message, AgentNote
│   │   ├── schemas/                   # Pydantic v2 request/response models
│   │   ├── api/v1/
│   │   │   ├── router.py              # Aggregates all v1 routers
│   │   │   ├── ws.py                  # GET /api/v1/ws  (auth via ?token=)
│   │   │   └── endpoints/
│   │   │       ├── auth.py            # POST /auth/login, GET /auth/me
│   │   │       ├── users.py           # GET /users/agents, POST /users (admin)
│   │   │       ├── conversations.py   # list/get/patch conversations
│   │   │       ├── messages.py        # agent replies (relayed via the contact's channel)
│   │   │       ├── notes.py           # internal agent notes
│   │   │       ├── quick_replies.py   # canned responses (list: all, write: admin)
│   │   │       ├── viber.py           # POST /viber/webhook (HMAC signature-verified)
│   │   │       ├── telegram.py        # POST /telegram/webhook (secret-token-verified)
│   │   │       └── diagnostics.py     # admin: per-channel account info / set_webhook
│   │   └── services/
│   │       ├── ws_manager.py          # WebSocket manager + broadcast
│   │       ├── inbound.py             # shared find-or-create conversation + persist + broadcast
│   │       ├── channels/
│   │       │   ├── base.py            # ChannelClient interface + ChannelSendResult
│   │       │   ├── viber.py           # Viber REST client + HMAC verification
│   │       │   ├── telegram.py        # Telegram Bot API client
│   │       │   └── registry.py        # channel name -> client lookup
│   │       └── serializers.py         # ORM -> JSON dicts (no lazy-load issues)
│   ├── init_db.py                     # create tables + seed admin/agent
│   ├── smoke_test.py                  # automated smoke test (mock Viber)
│   ├── mock_viber.py                  # local mock of the Viber REST API
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                       # routes: login, dashboard
│   │   ├── components/
│   │   │   ├── sidebar/               # ConversationList + StatusFilter
│   │   │   ├── conversation/          # thread, bubbles, composer, quick replies
│   │   │   └── panel/                 # AgentInfoPanel (assign/status/notes)
│   │   ├── hooks/                     # useWebSocket, useConversations
│   │   ├── lib/                       # api client, types, ws url, format utils
│   │   └── stores/                    # Zustand: authStore, chatStore
│   ├── package.json
│   ├── tailwind.config.ts
│   └── .env.example
└── README.md
```

## 0. Run with Docker (recommended)

Prerequisites: Docker Desktop running.

```bash
# optional: cp .env.example .env   # override passwords/ports/Viber token
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (docs at /docs when DEBUG=true)
- Postgres: localhost:5432, data in `pgdata` volume, uploads in `uploads` volume

Backend waits for Postgres and runs `init_db.py` automatically.
Bootstrap the first admin (no default passwords):

```bash
docker compose exec backend python create_admin.py --email you@company.com
```

Admins then manage the team at `/admin/users`.
Useful commands: `docker compose logs -f backend`, `docker compose down`,
`docker compose down -v` (deletes DB data).

## 1. Backend setup (local, without Docker)

Prerequisites: Python 3.11+, PostgreSQL 14+.

```bash
cd backend
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
Copy-Item .env.example .env        # Windows
# cp .env.example .env              # macOS / Linux
```

Start PostgreSQL (or use your own instance) and set `DATABASE_URL` in `.env`:

```bash
docker run --name shared-inbox-db \
  -e POSTGRES_USER=inbox -e POSTGRES_PASSWORD=inbox -e POSTGRES_DB=shared_inbox \
  -p 5432:5432 -d postgres:16
```

Create tables, bootstrap the first admin, and run:

```bash
python init_db.py
python create_admin.py --email you@company.com
uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- No default passwords. Admins manage the team at `/admin/users`
  (or `POST /api/v1/users`, `PATCH /api/v1/users/{id}`). Disabled logins get 401/403.

For production, use Alembic migrations (`alembic init`, then `alembic revision --autogenerate`)
instead of `create_all`, and set a real `SECRET_KEY`.

## 2. Frontend setup

Prerequisites: Node 18+.

```bash
cd frontend
npm install
Copy-Item .env.example .env.local   # Windows
# cp .env.example .env.local        # macOS / Linux
npm run dev
```

Open http://localhost:3000 and sign in.

## 3. Viber integration

1. Create a Viber Public Account / bot and copy its **Auth Token** into
   `backend/.env` → `VIBER_AUTH_TOKEN`.
2. The webhook URL must be publicly reachable (Viber pushes to it). Use ngrok/tunnel:
   ```bash
   ngrok http 8000
   ```
3. Point Viber at your backend (admin login required). Provide the base URL plus the webhook path:
   ```bash
   # Sign in to get a token first:
   curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}'

   # Use the returned access_token to register the webhook:
   curl -X POST http://localhost:8000/api/v1/diagnostics/viber/set-webhook \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://your-ngrok-host/api/v1/viber/webhook"}'
   ```
4. Verify connectivity:
   ```bash
   curl http://localhost:8000/api/v1/diagnostics/viber/account \
     -H "Authorization: Bearer <access_token>"
   ```

Every inbound Viber message now creates/updates a conversation and is pushed
live to all connected agent dashboards over WebSocket.

## 4. Telegram integration

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy its **token** into
   `backend/.env` → `TELEGRAM_BOT_TOKEN`. Generate a random string for
   `TELEGRAM_WEBHOOK_SECRET` (Telegram echoes it back on every webhook call so the
   backend can verify requests actually come from Telegram).
2. The webhook URL must be publicly reachable. Use ngrok/tunnel:
   ```bash
   ngrok http 8000
   ```
3. Point Telegram at your backend (admin login required):
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}'

   curl -X POST http://localhost:8000/api/v1/diagnostics/telegram/set-webhook \
     -H "Authorization: Bearer <access_token>" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://your-ngrok-host/api/v1/telegram/webhook"}'
   ```
4. Verify connectivity:
   ```bash
   curl http://localhost:8000/api/v1/diagnostics/telegram/account \
     -H "Authorization: Bearer <access_token>"
   ```

Every inbound Telegram message now creates/updates a conversation (kept separate
from Viber conversations by `channel`) and is pushed live to all connected agent
dashboards over WebSocket, exactly like Viber.

### Adding another channel

1. Add a value to `ChannelType` in `backend/app/models/conversation.py`.
2. Implement `ChannelClient` (`backend/app/services/channels/base.py`) for the
   new provider — see `viber.py` / `telegram.py` for the shape.
3. Register it in `backend/app/services/channels/registry.py`.
4. Add a webhook endpoint that verifies the request and calls
   `handle_inbound_message` / `handle_delivery_update` from `services/inbound.py`.
5. Wire the router in `api/v1/router.py` and add settings in `core/config.py`.

`messages.py` (agent replies + attachments) and the dashboard already work with
any channel through `get_channel_client(conversation.channel)` — no changes needed there.

## WebSocket events (server -> client)

| Event                  | Payload                                            |
| ---------------------- | -------------------------------------------------- |
| `message:new`          | `{ message, conversation }` (fresh inbound/outbound) |
| `conversation:updated` | full conversation object (assignment / status)      |
| `message:status`       | `{ message_id, conversation_id, status }` (delivered/seen) |

## Quick replies & alerts

- **Quick replies** live in the `quick_replies` table. Admins manage them at
  `/admin/quick-replies` (or `GET/POST /api/v1/quick-replies`,
  `PATCH/DELETE /api/v1/quick-replies/{id}`); every agent sees them under the
  composer's *Quick Replies* button. Picking one inserts its text into the reply
  box so it can be edited before sending.
- **New-message alerts**: when a contact writes, the dashboard plays a short chime,
  and — if the tab is in the background — shows a desktop notification (click it to
  jump to the conversation) and an unread count in the tab title. Nothing fires for
  the conversation you're currently looking at. The bell icon in the header turns
  alerts on/off (saved per browser) and asks for desktop-notification permission.

## Photos, video, voice & emoji

Agents can send photos, videos, audio and files (paperclip), record voice messages
(microphone button) and insert emoji (smiley button). Each attachment goes out as the
richest type the channel accepts:

| Attachment | Telegram | Viber |
| --- | --- | --- |
| Photo | `sendPhoto` (≤10 MB, GIFs as document) | `picture` (JPEG/PNG/GIF ≤1 MB), else file |
| Video | `sendVideo` (MP4), else document | `video` (MP4 ≤26 MB), else file |
| Voice recording | `sendVoice` (re-encoded to OGG/Opus with ffmpeg) | file |
| Anything else | `sendDocument` | file |

Inbound Telegram photos, videos, voice notes, audio, stickers and documents are
downloaded by the backend and re-hosted under `/uploads` (Telegram's file links embed
the bot token, so they are never stored or shown to browsers). Animated stickers
show their emoji.

Notes:
- **ffmpeg** converts voice recordings; the Docker image includes it. Running the
  backend without Docker, install ffmpeg or recordings are sent as plain files.
- The microphone only works on `https://` or `localhost` (browser rule).
- Telegram attachments are uploaded directly, so they work with the default
  `PUBLIC_BASE_URL`. **Viber** fetches media from a URL, so for Viber set
  `PUBLIC_BASE_URL` to your public address (e.g. the ngrok URL).
- `/uploads` is served without auth; stored names include a random 128-bit id.

## Smoke test (no real Viber token needed)

Uses a local mock Viber API so every flow can be exercised offline.

```bash
# 1. Start PostgreSQL, seed, and run the backend
docker run --name shared-inbox-db -e POSTGRES_USER=inbox -e POSTGRES_PASSWORD=inbox \
  -e POSTGRES_DB=shared_inbox -p 5432:5432 -d postgres:16
cd backend
python init_db.py

# 2. Mock Viber API (answers /pa calls with status:0 and unique message tokens)
python mock_viber.py 9000

# 3. Backend pointed at the mock (separate terminal)
$env:VIBER_API_BASE_URL = "http://localhost:9000/pa"   # PowerShell
uvicorn app.main:app --reload --port 8000

# 4. Run the smoke test
python smoke_test.py
```

`smoke_test.py` automates the whole flow and prints a PASS/FAIL per step:
login + RBAC, bad-login rejection, Viber webhook (+signature check) creating a
conversation, status filters, internal note, agent text reply, attachment upload
(+ file served back), assignment/status patch, and unauthenticated access.

## Notes / next steps

- RBAC: endpoints use `require_roles(UserRole.admin)` for admin-only actions
  (create user, diagnostics). Agents can manage all conversations.
- `smoke_test.py` currently only exercises the Viber path; the Telegram webhook
  is best verified against the real Bot API (or a `getMe`/`sendMessage` mock)
  since it isn't HMAC-signed the way Viber's is.
- A conversation belongs to exactly one channel; a contact who reaches out on
  two channels shows up as two separate conversations. Merge-by-identity across
  channels is a reasonable next step if you need it.