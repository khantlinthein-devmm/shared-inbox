# Real Viber E2E checklist (no mocks, no automated sends)

`backend/smoke_test.py` is mock-only for dev/staging. This checklist is the
separate real-Viber path. Nothing here sends messages or calls Viber by itself.

## 0. What you must obtain manually

| Value | Where | Goes into |
|---|---|---|
| `<REAL_VIBER_BOT_TOKEN>` | Viber Admin panel -> your bot -> Auth Token | `backend/.env` -> `VIBER_AUTH_TOKEN` |
| `<PUBLIC_BACKEND_URL>` | `ngrok http 8000` output, e.g. `xxxx.ngrok-free.app` | `VIBER_WEBHOOK_URL`, `PUBLIC_BASE_URL` |
| Admin login | `python create_admin.py --email you@company.com` | login to get JWT for diagnostics |

Expected env (placeholders, never commit real token):
```env
VIBER_AUTH_TOKEN=<REAL_VIBER_BOT_TOKEN>
VIBER_WEBHOOK_URL=https://<PUBLIC_BACKEND_URL>/api/v1/viber/webhook
PUBLIC_BASE_URL=https://<PUBLIC_BACKEND_URL>
VIBER_API_BASE_URL=https://chatapi.viber.com/pa
```

## 1. Offline config check (no network, no Viber call)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ..\scripts\check_viber_config.py --env .env
# prod file: python ..\scripts\check_viber_config.py --env .env.production
```

Fix every `FAIL` before continuing. `WARN` is OK for local test only
(e.g. `DEBUG=true`, `CORS_ORIGINS` localhost).

## 2. Start locally + expose

```powershell
# terminal 1
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend
npm run dev
# http://localhost:3000

# terminal 3 - do NOT hardcode this URL in source
ngrok http 8000
```

Restart backend after any `.env` change (`ViberClient` binds token at import,
`get_settings()` is cached).

## 3. Register + verify webhook (admin JWT required)

```powershell
$login = Invoke-RestMethod -Method POST http://localhost:8000/api/v1/auth/login `
  -ContentType "application/json" `
  -Body '{"email":"admin@example.com","password":"<ADMIN_PASSWORD>"}'
$h = @{ Authorization = "Bearer $($login.access_token)" }

# health of real token (200 = good, 502 invalidAuthToken = bad token)
Invoke-RestMethod http://localhost:8000/api/v1/diagnostics/viber/account -Headers $h

# register - prefer explicit url over env fallback
Invoke-RestMethod -Method POST http://localhost:8000/api/v1/diagnostics/viber/set-webhook `
  -Headers $h -ContentType "application/json" `
  -Body '{"url":"https://<PUBLIC_BACKEND_URL>/api/v1/viber/webhook"}'
```

Endpoints: `POST /api/v1/auth/login` (`app/api/v1/endpoints/auth.py:15`),
admin guard `require_roles(admin)` (`app/core/deps.py:32`),
`GET /diagnostics/viber/account` (`diagnostics.py:17`),
`POST /diagnostics/viber/set-webhook` (`diagnostics.py:28`,
`url = payload.url or settings.viber_webhook_url`).

## 4. Manual phone sequence

1. Phone Viber -> subscribe to bot -> send `hello e2e HH:MM`.
2. Dashboard `http://localhost:3000/dashboard` shows WS `Live`.
   New `unassigned` conversation arrives via `message:new`
   (`viber.py:130`, `ws_manager.py:43`).
3. Agent assigns to self, sets `open`, adds internal note.
4. Agent replies from composer -> `POST /conversations/{id}/messages`
   (`messages.py:46`) sends via real `send_text`. Phone receives it.
5. Viber callbacks `delivered` then `seen` (`viber.py:133`) update the bubble
   via `message:status`.
6. Attachment: send small file from dashboard. Requires
   `PUBLIC_BASE_URL=https://<PUBLIC_BACKEND_URL>` otherwise Viber cannot
   fetch `/uploads/...` (`messages.py:134`, `main.py:45`).

## 5. Safety

* Never put the real token in source, chat logs, or git. `.env` only.
* `smoke_test.py` + `mock_viber.py` stay mock-only. Keep runs separate.
* This checklist never sends messages itself; only your phone + dashboard do.
