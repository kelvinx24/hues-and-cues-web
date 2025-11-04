import logging
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Websocket connected. Total connections: {len(self.active_connections)}")

    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"Websocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message:dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending message to webSocket: {e}")
                disconnected.append(connection)

        for connection in disconnected:
            self.active_connections.remove(connection)