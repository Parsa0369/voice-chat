from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pathlib import Path
import json

app = FastAPI(title="Voice Chat")

rooms: dict[str, set[WebSocket]] = {}

INDEX = Path(__file__).parent / "templates" / "index.html"

@app.get("/", response_class=HTMLResponse)
async def home():
    return INDEX.read_text(encoding="utf-8")

@app.get("/room/{room_id}", response_class=HTMLResponse)
async def room(room_id: str):
    return INDEX.read_text(encoding="utf-8")

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    room = rooms.setdefault(room_id, set())

    # This first message tells the client whether it is the first or second peer.
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

    # Tell the existing peer to create the WebRTC offer.
    if len(room) == 2:
        peers = list(room)
        try:
            await peers[0].send_text(json.dumps({"type": "ready", "role": "caller"}))
            await peers[1].send_text(json.dumps({"type": "ready", "role": "callee"}))
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
