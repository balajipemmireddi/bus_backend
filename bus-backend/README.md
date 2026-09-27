# Backend — Quick Setup (Dev Speed Version)

Built for speed to get you an end-to-end working system fast. Uses SQLite, not
Postgres — swap that out before real multi-bus production (see main spec §4), but
for a demo/pilot with one or a few buses this is genuinely fine and much faster
to stand up.

## Run it (on your laptop, or any machine reachable from the Pi's network)

```bash
pip install -r requirements.txt
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` matters — it makes the server reachable from other devices on
your network (like the Pi), not just from the machine it's running on.

Find this machine's IP address (so the Pi knows where to send data):
- Windows: `ipconfig` (look for IPv4 Address)
- Mac/Linux: `ifconfig` or `ip addr`

Visit `http://<this-machine-IP>:8000/docs` in a browser — FastAPI gives you a
free interactive API tester, useful for poking at endpoints by hand.

## Connect the Pi to it

On the Pi:

```bash
pip install requests --break-system-packages
cd ~/Desktop/bus-edge-app
python3 sync_client.py --backend-url http://<BACKEND-MACHINE-IP>:8000 --bus-id bus_14
```

This does one sync pass: pushes any queued events, pulls the latest roster. Add
`--loop` to run it continuously every 30 seconds instead of once:

```bash
python3 sync_client.py --backend-url http://<BACKEND-MACHINE-IP>:8000 --bus-id bus_14 --loop
```

## Enroll a student directly into the backend (skips the Pi for this step)

```bash
curl -X POST http://<BACKEND-MACHINE-IP>:8000/api/enroll -H "Content-Type: application/json" -d '{
  "child_id": "child_001", "name": "Test Student",
  "encodings": [[0.1,0.2,0.3]],
  "assigned_bus_id": "bus_14", "pickup_stop_id": "stop_1", "drop_stop_id": "stop_1"
}'
```

(In the real flow, you'd enroll via `enroll_student.py` on the Pi with real
photos, which generates real encodings — this curl example is just for quickly
testing the backend's plumbing with fake numbers.)

## Endpoints available right now

- `POST /api/enroll` — add/update a student
- `GET /api/bus/{bus_id}/roster` — full roster (every bus gets everything, §12)
- `POST /api/events` — edge devices push events here (called by `sync_client.py`)
- `GET /api/review` — pending review-queue items (low-confidence matches)
- `POST /api/review/{event_id}/resolve?decision=confirmed&confirmed_child_id=X` — resolve one
- `GET /api/live` — most recent events across all buses (the live feed for §10)

## What's stubbed / not real yet

- **WhatsApp sending** — when a PICKED_UP/DROPPED event lands, it just prints
  `[WOULD SEND WHATSAPP] ...` to the server console instead of actually sending.
  Wiring in the real Meta Cloud API is Phase 6 — separate piece of work, needs a
  registered WhatsApp Business account first.
- **No admin dashboard UI yet** — everything above is API-only. `/docs` gives
  you a testable interface in the meantime.
- **SQLite, not Postgres** — fine for one demo/pilot bus, not for the full fleet.
