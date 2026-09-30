from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pathlib import Path
import json
import os
import httpx

app = FastAPI(title="Voice Chat")
rooms: dict[str, set[WebSocket]] = {}
INDEX = Path(__file__).parent / "templates" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX.read_text(encoding="utf-8")


@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room(room_id: str):
    return INDEX.read_text(encoding="utf-8")


@app.get("/sw.js")
async def service_worker():
    return Response(
        content=r"""
const NOTIFICATION_TAG = "voice-chat-call";

self.addEventListener("notificationclick", event => {
  const action = event.action;
  const data = event.notification?.data || {};
  event.notification.close();

  event.waitUntil((async () => {
    const clientsList = await self.clients.matchAll({
      type: "window",
      includeUncontrolled: true
    });

    const roomUrl = data.roomUrl || "/";

    let client = clientsList.find(c => {
      try { return new URL(c.url).pathname === new URL(roomUrl, self.location.origin).pathname; }
      catch { return false; }
    });

    if (!client) client = clientsList[0];

    if (client) {
      if ("focus" in client) await client.focus();
      for (const target of clientsList) {
        try { target.postMessage({ type: "notification-action", action }); } catch {}
      }
      return;
    }

    if (self.clients.openWindow) {
      const opened = await self.clients.openWindow(roomUrl);
      if (opened) {
        setTimeout(() => {
          try { opened.postMessage({ type: "notification-action", action }); } catch {}
        }, 1500);
      }
    }
  })());
});

self.addEventListener("notificationclose", () => {});
""",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"}
    )


@app.get("/manifest.webmanifest")
async def manifest():
    return Response(
        content=json.dumps({
            "name": "Voice Chat",
            "short_name": "Voice Chat",
            "description": "تماس صوتی دو نفره",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#080b16",
            "theme_color": "#11182b",
            "lang": "fa",
            "dir": "rtl"
        }),
        media_type="application/manifest+json"
    )


@app.get("/turn-credentials")
async def turn_credentials():
    key_id = os.getenv("CF_TURN_KEY_ID")
    api_token = os.getenv("CF_TURN_API_TOKEN")

    if not key_id or not api_token:
        return JSONResponse(
            {"enabled": False, "message": "TURN credentials are not configured on the server."},
            status_code=503
        )

    url = f"https://rtc.live.cloudflare.com/v1/turn/keys/{key_id}/credentials/generate-ice-servers"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json"
                },
                json={"ttl": 3600}
            )
            response.raise_for_status()
            data = response.json()

        return JSONResponse({
            "enabled": True,
            "iceServers": data.get("iceServers", [])
        })
    except Exception as exc:
        return JSONResponse(
            {"enabled": False, "message": "TURN credential generation failed."},
            status_code=502
        )


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    room = rooms.setdefault(room_id, set())

    if len(room) >= 2:
        await websocket.send_text(json.dumps({
            "type": "full",
            "message": "این اتاق پر است."
        }))
        await websocket.close()
        return

    room.add(websocket)
    await websocket.send_text(json.dumps({
        "type": "joined",
        "peers": len(room)
    }))

    if len(room) == 2:
        peers = list(room)
        try:
            await peers[0].send_text(json.dumps({
                "type": "ready",
                "role": "caller"
            }))
            await peers[1].send_text(json.dumps({
                "type": "ready",
                "role": "callee"
            }))
        except Exception:
            pass

    try:
        while True:
            message = await websocket.receive_text()
            for peer in list(room):
                if peer is not websocket:
                    try:
                        await peer.send_text(message)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        room.discard(websocket)
        if not room:
            rooms.pop(room_id, None)
        else:
            for peer in list(room):
                try:
                    await peer.send_text(json.dumps({"type": "peer-left"}))
                except Exception:
                    pass
