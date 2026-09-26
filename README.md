# Shared Inbox — Multi-Agent Viber Customer Support Dashboard

A production-ready skeleton for a shared inbox that lets support agents handle
Viber conversations in real time.

- **Backend**: FastAPI, Async WebSockets, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL, JWT auth + RBAC
- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Zustand, WebSockets, Lucide icons
- **Messaging**: Viber Bot API (webhook ingest + REST messaging client, signature verification)

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
│   │   │       ├── messages.py        # agent replies (relayed to Viber)
│   │   │       ├── notes.py           # internal agent notes
│   │   │       ├── viber.py           # POST /viber/webhook (signature-verified)
│   │   │       └── diagnostics.py     # admin: Viber account info / set_webhook
│   │   └── services/
│   │       ├── ws_manager.py          # WebSocket manager + broadcast
│   │       ├── viber_client.py        # Viber REST client + HMAC verification
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

## WebSocket events (server -> client)

| Event                  | Payload                                            |
| ---------------------- | -------------------------------------------------- |
| `message:new`          | `{ message, conversation }` (fresh inbound/outbound) |
| `conversation:updated` | full conversation object (assignment / status)      |
| `message:status`       | `{ message_id, conversation_id, status }` (delivered/seen) |

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

- Quick Replies are a static list in `frontend/src/lib/quickReplies.ts` — move to
  a backend-driven list when you need per-team management.
- RBAC: endpoints use `require_roles(UserRole.admin)` for admin-only actions
  (create user, diagnostics). Agents can manage all conversations.