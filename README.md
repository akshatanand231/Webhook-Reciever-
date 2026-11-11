# Lightweight Python Webhook Receiver

A small FastAPI service that accepts JSON webhooks and stores each event in SQLite.

## Endpoints

- `GET /` — service information
- `GET /health` — health check
- `POST /webhook` — receives and stores a JSON payload
- `GET /events?limit=20` — returns the latest stored events (1–100)

## Run locally

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `WEBHOOK_API_KEY` to a long random secret.
Export the variables in your terminal (or use your preferred dotenv loader), then run:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

For a quick local test without authentication, leave `WEBHOOK_API_KEY` unset.
Open `http://127.0.0.1:8000/docs` to inspect and test the API.

## Send a test webhook

```bash
curl -X POST http://127.0.0.1:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: replace-with-a-long-random-secret" \
  -d '{"order_id":"ORD12345","status":"shipped","courier":"DHL"}'
```

If authentication is enabled, the sender must include the `X-Webhook-Secret` header.
The server responds with HTTP 200 and an event ID after storing the payload.

## Deploy to Render

1. Create a Git repository and push these project files.
2. In Render, choose **New +** → **Blueprint**, then connect the repository.
3. Render reads `render.yaml` and creates the web service and persistent disk.
4. After deployment, copy the service URL, e.g. `https://your-service.onrender.com`.
5. Configure the source application to send `POST` requests to:
   `https://your-service.onrender.com/webhook`
6. If Render generated `WEBHOOK_API_KEY`, open the service environment settings and copy its value into the sender's `X-Webhook-Secret` header field.

## Important production notes

- The `/events` endpoint currently has no authentication. Do not expose it publicly as-is if webhook payloads contain business or customer data. Restrict it, add authentication, or remove it before production use.
- Use the persistent disk configured in `render.yaml`; otherwise local SQLite data may be lost on redeploy/restart.
- Configure provider-side webhook signatures/IP allowlists where supported. The shared secret header is a simple baseline, not a substitute for provider signature verification.
- Confirm the hosting provider's current pricing and persistent-disk availability before deployment.
- This starter receives JSON only. It does not yet transform or forward payloads.
