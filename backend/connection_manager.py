from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.player_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        print(f"🔌 {player_id} connected to game {session_id}")

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
            
        self.active_connections[session_id].append(websocket)
        self.player_connections[player_id] = websocket

    

    def disconnect(self, session_id: str, player_id: str):
        if player_id in self.player_connections:
            websocket = self.player_connections[player_id]

            if session_id in self.active_connections:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
                
                del self.player_connections[player_id]

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all sockets in the given game."""
        if session_id in self.active_connections:
            for ws in self.active_connections[session_id]:
                await ws.send_json(message)

    async def broadcast_to_player(self, player_id: str, message: dict):
        if player_id in self.player_connections:
            ws = self.player_connections[player_id]
            try:
                await ws.send_json(message)
            except Exception as e:

                print("Could not send to player with id " + player_id)

# global instance
manager = ConnectionManager()
