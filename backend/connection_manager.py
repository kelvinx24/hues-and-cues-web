from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        # session_id -> list of WebSockets
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # player_id -> WebSocket
        self.player_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, player_id: str, websocket: WebSocket):
        await websocket.accept()
        print(f"🔌 {player_id} connected to game {session_id}")

        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
            
        self.active_connections[session_id].append(websocket)
        self.player_connections[player_id] = websocket

    async def disconnect(self, session_id: str, player_id: str, socketOpen: bool = True):
        if player_id in self.player_connections:
            websocket = self.player_connections[player_id]

            if session_id in self.active_connections:
                # Safely remove socket from list
                if websocket in self.active_connections[session_id]:
                    self.active_connections[session_id].remove(websocket)

                # Clean up session if empty
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]

            # Always remove from player map last
            del self.player_connections[player_id]
        
            try:
                await websocket.close()
                return True
            except RuntimeError:
                return False
            

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Send a message to all players in a given session."""
        if session_id in self.active_connections:
            for ws in list(self.active_connections[session_id]):  # list() to avoid mutation issues
                try:
                    await ws.send_json(message)
                except Exception as e:
                    print(f"❌ Failed to send to session {session_id}: {e}")

    async def broadcast_to_player(self, player_id: str, message: dict):
        """Send a message to a specific player."""
        if player_id in self.player_connections:
            ws = self.player_connections[player_id]
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"❌ Could not send to player {player_id}: {e}")

    async def broadcast_game_state(self, game, event: Optional[str] = "game_update", exclude_colors=True):
        """Send each player a personalized view of the game state."""
        for p in game.players:
            player_id = p.player_id
            data = {
                "event": event,
                "data": game.to_dict(for_player_id=player_id, exclude_colors=exclude_colors)
            }

            await self.broadcast_to_player(player_id, data)

# global instance
manager = ConnectionManager()
