from fastapi import FastAPI, Body, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated, List, Optional, Dict
import random
import uuid

import json
from connection_manager import manager

from player import Player
from game import Game

app = FastAPI(title="Hues and Cues Game API")

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




class CreateJoinSessionRequest(BaseModel):
    name: str

class LeaveSessionRequest(BaseModel):
    player_id: str

class Session(BaseModel):
    session_id: str
    leader: Player
    players: List[Player] = []
    current_game: Optional[Game] = None

    def active_game(self):
        return self.current_game != None



class Clue(BaseModel):
    player_id: str
    clue_text: str

# Game state storage (in-memory for simplicity)
sessions: Dict[str, Session] = {}
players: Dict[str, Player] = {}

@app.get("/")
def read_root():
    return {"message": "Hues and Cues Game API", "status": "running"}

async def broadcast_to_rest(session_id: str, message: dict):
    if session_id not in sessions:
        return
    
    session = sessions[session_id]
    game = session.current_game
    if game is not None:
        for player in session.players:
            if player.player_id == game.current_player:
                continue

            await manager.broadcast_to_player(player.player_id, message)

async def broadcast_to_current_player(session_id: str, message: dict):
    if session_id not in sessions:
        return
    
    session = sessions[session_id]
    game = session.current_game
    if game is not None:
        await manager.broadcast_to_player(game.current_player, message)
                



@app.websocket("/ws/{session_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, player_id: str):
    print("Active sessions:", list(sessions.keys()))
    print("Active players:", list(players.keys()))
    if session_id not in sessions or player_id not in players:
        await websocket.close(code=1008)
        print(f"Invalid session {session_id} or player {player_id}")
        return
        


    await manager.connect(session_id, player_id, websocket)

    current_session = sessions[session_id]

    await manager.broadcast_to_session(
        session_id,
        {
            "event": "player_joined",
            "data": current_session.model_dump(),
        },
    )

    try:
        while True:
            # We can listen if players send messages too
            data = await websocket.receive_text()
            print(f"Received from {player_id}: {data}")
            await current_session.current_game.handle_action(data)
    except WebSocketDisconnect:
        print(f"❌ {player_id} disconnected from game {session_id}")
        await leave_game(session_id, LeaveSessionRequest(player_id=player_id))

    


@app.post("/session/create")
def create_session(entered_name: CreateJoinSessionRequest):
    """Create a new game room"""
    new_session_id = str(uuid.uuid4())[:8]
    new_player_id = str(uuid.uuid4())[:8]
    player = Player(
        player_id = new_player_id,
        name = entered_name.name,
    )
    
    players[new_player_id] = player

    new_session = Session(
        session_id = new_session_id,
        leader = player
    )
    new_session.players.append(player)
    
    sessions[new_session_id] = new_session
    response = dict(new_session.model_dump())
    response["you"] = new_player_id
    print(f"Created session {new_session_id} with player {new_player_id}")

    return response

@app.post("/session/{session_id}/join")
def join_game(session_id: str, entered_name: CreateJoinSessionRequest):
    """Join an existing game"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]
    
    if len(session.players) >= 10:
        raise HTTPException(status_code=400, detail="Game is full")
    
    new_player_id = str(uuid.uuid4())[:8]
    player = Player(
        player_id = new_player_id,
        name = entered_name.name,
    )
    
    session.players.append(player)
    players[new_player_id] = player
    response = dict(session.model_dump())
    response['you'] = new_player_id
    
    return response

@app.post("/session/{session_id}/leave")
async def leave_game(session_id: str, leaveReq: LeaveSessionRequest):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]

    player_id = leaveReq.player_id
    if player_id not in players:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player = players[player_id]

    session.players.remove(player)

    manager.disconnect(session_id, player_id)
    
    await manager.broadcast_to_session(
        session_id,
        {
            "event": "player_left",
            "data": session.model_dump(),
        },
    )
    
    return {"status": "success", "message": "game left"}

    
@app.post("/session/{session_id}/start")
async def start_game(session_id: str, player_id: str):
    """Start the game"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]
    if len(session.players) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")
    if session.leader.player_id != player_id:
        raise HTTPException(status_code=400, detail="Only lobby leader can start")
    if session.active_game() != False:
        raise HTTPException(status_code=403, detail="Game in progress")
    
    # Create Game
    # Pick random target color
    
    
    # Pick random starting player
    
    new_game_id = str(uuid.uuid4())[:8]

    game = Game(
        game_id=new_game_id,
        session_id=session_id,
        players=session.players,
    )


    session.current_game = game

    await game.startup()
    
    return {"status": "success", "message": "game created"}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
