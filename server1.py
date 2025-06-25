from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict

app = FastAPI()

# Holds clients waiting to be paired
waiting_clients = []

# Paired rooms: room_id -> (client_a, client_b)
paired_clients: Dict[str, tuple] = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Pair the client with another if waiting
    if waiting_clients:
        peer = waiting_clients.pop()
        room_id = f"{id(peer)}-{id(websocket)}"
        paired_clients[room_id] = (peer, websocket)
        await peer.send_text("✅ Paired! You can start chatting.")
        await websocket.send_text("✅ Paired! You can start chatting.")
    else:
        waiting_clients.append(websocket)
        await websocket.send_text("⏳ Waiting for a partner...")

    try:
        while True:
            message = await websocket.receive_text()
            
            # Find the room this socket belongs to
            for room_id, (client_a, client_b) in paired_clients.items():
                if websocket == client_a:
                    await client_b.send_text(f"Partner: {message}")
                    break
                elif websocket == client_b:
                    await client_a.send_text(f"Partner: {message}")
                    break

    except WebSocketDisconnect:
        # Clean up disconnected clients
        if websocket in waiting_clients:
            waiting_clients.remove(websocket)
        else:
            to_remove = None
            for room_id, (client_a, client_b) in paired_clients.items():
                if websocket in (client_a, client_b):
                    other = client_b if websocket == client_a else client_a
                    await other.send_text("❌ Your partner disconnected.")
                    await other.close()
                    to_remove = room_id
                    break
            if to_remove:
                del paired_clients[to_remove]
