# Shared Inbox — Multi-Agent Omni-Channel Customer Support Dashboard

A production-ready skeleton for a shared inbox that lets support agents handle
conversations from multiple messaging channels, in one dashboard, in real time.

- **Backend**: FastAPI, Async WebSockets, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL, JWT auth + RBAC
- **Frontend**: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Zustand, WebSockets, Lucide icons
- **Messaging**: **Viber**, **Telegram**, **Facebook Messenger** and **WhatsApp** (Cloud API),
  behind one channel-agnostic `ChannelClient` interface (`backend/app/services/channels/`).
  Admins connect channels on the **Channels** page — no `.env` editing needed. The
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
│   │   │       ├── channels.py        # admin: connect/disconnect channels, public URL
│   │   │       ├── viber.py           # POST /viber/webhook (HMAC signature-verified)
│   │   │       ├── telegram.py        # POST /telegram/webhook (secret-token-verified)
│   │   │       ├── messenger.py       # GET/POST /messenger/webhook (Meta-signed)
│   │   │       └── whatsapp.py        # GET/POST /whatsapp/webhook (Meta-signed)
│   │   └── services/
│   │       ├── ws_manager.py          # WebSocket manager + broadcast
│   │       ├── inbound.py             # shared find-or-create conversation + persist + broadcast
│   │       ├── channel_store.py       # channel credentials (UI, encrypted) with .env fallback
│   │       ├── channels/
│   │       │   ├── base.py            # ChannelClient interface + ChannelSendResult
│   │       │   ├── viber.py           # Viber REST client + HMAC verification
│   │       │   ├── telegram.py        # Telegram Bot API client
│   │       │   ├── meta.py            # shared Graph API plumbing (Messenger + WhatsApp)
│   │       │   ├── messenger.py       # Messenger Send API client
│   │       │   ├── whatsapp.py        # WhatsApp Cloud API client
│   │       │   └── registry.py        # builds a client from the channel's stored config
│   │       └── serializers.py         # ORM -> JSON dicts (no lazy-load issues)
│   ├── init_db.py                     # apply database migrations (runs on start)
│   ├── migrations/                    # Alembic migration scripts
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

For production, set a real `SECRET_KEY`.

### Database migrations

The schema is managed by Alembic (`backend/migrations`). `python init_db.py` (run
automatically on every container start) applies any pending migrations, so pulling
new code and restarting never requires wiping the database. Databases created before
migrations existed are detected and adopted in place, keeping their data.

To change the schema, edit the models and generate a migration:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
```

Review the generated file in `migrations/versions/`, commit it, and restart.

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

## 3. Connecting channels (Channels page)

Sign in as an admin and open **Channels** in the header. Everything is done there;
credentials are validated with the provider before they're saved, stored encrypted
(key derived from `SECRET_KEY` — set a real one, and note that changing it means
reconnecting channels), and only their last 4 characters are ever shown again.

1. **Public server URL** — messaging apps must reach the backend over https. Run a
   tunnel such as `ngrok http 8000` and paste its https address. Whenever it changes,
   update it here: Telegram and Viber webhooks are re-registered automatically.
2. **Telegram** — create a bot with [@BotFather](https://t.me/BotFather) (`/newbot`),
   paste the bot token, **Connect**. The webhook and its secret are set up for you.
3. **Viber** — create a bot at [partners.viber.com](https://partners.viber.com), paste its
   auth token, **Connect**. The webhook is registered for you.
4. **Messenger** — in a [Meta app](https://developers.facebook.com/apps) with the
   Messenger product: generate a **Page access token** for your Page and copy the
   **App secret** (App settings → Basic). Paste both, **Connect**, then in the Meta
   dashboard (Messenger → Webhooks) paste the **Callback URL** and **Verify token**
   shown on the card and subscribe to `messages`, `message_deliveries`, `message_reads`.
5. **WhatsApp** — in a Meta app with the WhatsApp product: copy the **Phone number
   ID** (WhatsApp → API Setup), create a permanent **System User access token** with
   `whatsapp_business_messaging`, and copy the **App secret**. Paste them, **Connect**,
   then add the card's **Callback URL** and **Verify token** under WhatsApp →
   Configuration → Webhook and subscribe to `messages`.

Each card also has an optional **auto-reply**. Messenger and WhatsApp only allow free-form
replies within 24 hours of the customer's last message (Meta policy); outside that window
the send fails with Meta's error shown in the composer.

The older `VIBER_*` / `TELEGRAM_*` settings in `.env` still work: such a channel shows as
*Connected (.env)*. Connecting it on the page overrides `.env`; disconnecting the page's
config falls back to `.env` again.

### Adding another channel

1. Add a value to `ChannelType` in `backend/app/models/conversation.py`.
2. Implement `ChannelClient` (`backend/app/services/channels/base.py`) for the
   provider — see `telegram.py` / `whatsapp.py` for the shape — and build it in
   `registry.py`'s `build_client`.
3. Add its fields to `REQUIRED` and its connect check in `api/v1/endpoints/channels.py`,
   and a card in `frontend/src/app/admin/channels/page.tsx`.
4. Add a webhook endpoint that reads its config with `get_config()`, verifies the
   request, and calls `handle_inbound_message` / `handle_delivery_update` from
   `services/inbound.py`. Wire it in `api/v1/router.py`.

`messages.py` (agent replies + attachments) and the dashboard already work with
any channel through `get_channel_client(conversation.channel)` — no changes needed there.

## WebSocket events (server -> client)

| Event                  | Payload                                            |
| ---------------------- | -------------------------------------------------- |
| `message:new`          | `{ message, conversation }` (fresh inbound/outbound) |
| `conversation:updated` | full conversation object (assignment / status)      |
| `message:status`       | `{ message_id, conversation_id, status }` (delivered/seen) |

### Unread, reopening and "Mine"

- Each conversation counts contact messages no agent has looked at yet; the sidebar
  shows the count as a badge. It clears for the whole team when an agent opens the
  conversation (tab visible and focused) or replies in it.
- A contact writing into a **closed** or **pending** conversation reopens it — as
  *Open* if it's assigned, otherwise *Unassigned* — so it can't be missed.
- The **Mine** filter shows only conversations assigned to you; it combines with the
  status tabs.

### Sent / delivered / seen

Agent messages show ✓ **Sent**, ✓✓ **Delivered** and blue ✓✓ **Seen**; the latest
one also spells its status out.

- **Viber** reports delivery and reads through its `delivered` / `seen` callbacks.
  A late `delivered` never downgrades a message that's already seen.
- **Telegram** gives bots no delivery or read receipts, so its messages stay *Sent*
  until the customer replies — a reply marks every earlier agent message *Seen*
  (on any channel). Hovering a Telegram *Sent* tick explains this.

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

| Attachment | Telegram | Viber | Messenger | WhatsApp |
| --- | --- | --- | --- | --- |
| Photo | `sendPhoto` (≤10 MB, GIFs as document) | `picture` (JPEG/PNG/GIF ≤1 MB), else file | image | image (JPEG/PNG), else document |
| Video | `sendVideo` (MP4), else document | `video` (MP4 ≤26 MB), else file | video | video (MP4/3GP), else document |
| Voice recording | `sendVoice` (re-encoded to OGG/Opus with ffmpeg) | file | audio | audio (shows as a voice note) |
| Anything else | `sendDocument` | file | file | document |

Inbound photos, videos, voice notes, audio, stickers and documents from Telegram,
Messenger and WhatsApp are downloaded by the backend and re-hosted under `/uploads`
(provider links expire, and Telegram's embed the bot token, so they are never stored or
shown to browsers). Stored links are host-relative (`/uploads/…`), so they keep working
when the public URL changes. Animated Telegram stickers show their emoji.

Notes:
- **ffmpeg** converts voice recordings. It's bundled via the `imageio-ffmpeg` pip
  package (a system `ffmpeg` on PATH is used instead if present); if neither
  works, recordings are sent as plain files.
- The microphone only works on `https://` or `localhost` (browser rule).
- Telegram, Messenger and WhatsApp attachments are uploaded directly. **Viber** fetches
  media from a URL, so Viber attachments need the public URL set on the Channels page.
- `/uploads` is served without auth; stored names include a random 128-bit id.

## Voice & video calls (Jitsi Meet)

Viber and Telegram bot APIs can't place or receive calls, so calls run on
[Jitsi Meet](https://jitsi.org/) in the browser. The phone / camera buttons in the
conversation header create a random room, send the contact the join link through
their channel (`CALL_INVITE_TEMPLATE`), and open the call for the agent in a new tab.
The thread shows a call card with a **Join** button to rejoin.

- `JITSI_DOMAIN` defaults to the public `meet.jit.si`, which is fine for trying it
  out; there the first person in a room must sign in (Google/GitHub) to start it.
  For production, [self-host Jitsi](https://jitsi.github.io/handbook/docs/devops-guide/devops-guide-docker)
  or use an 8x8 JaaS domain.
- Room names carry 128 random bits, so only people with the link can join; there's
  no lobby or password.
- Customers join from the link in their phone's browser or the Jitsi Meet app.

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
  (create user, channel settings, quick replies). Agents can manage all conversations.
- `smoke_test.py` currently only exercises the Viber path; the Telegram webhook
  is best verified against the real Bot API (or a `getMe`/`sendMessage` mock)
  since it isn't HMAC-signed the way Viber's is.
- A conversation belongs to exactly one channel; a contact who reaches out on
  two channels shows up as two separate conversations. Merge-by-identity across
  channels is a reasonable next step if you need it.