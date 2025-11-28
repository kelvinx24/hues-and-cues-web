from fastapi import FastAPI, Body, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
import uuid

from backend.session import Session
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
    """ Request model for creating or joining a session.
    Attributes:
        name (str): The name of the player.
    """
    
    name: str

class LeaveSessionRequest(BaseModel):
    """ Request model for leaving a session.
    Attributes:
        player_id (str): The ID of the player leaving the session.
    """
    
    player_id: str

# Game state storage (in-memory for simplicity)
sessions: Dict[str, Session] = {}
players: Dict[str, Player] = {}

@app.get("/")
def read_root():
    """
    Basic health check endpoint
    """
    return {"message": "Hues and Cues Game API", "status": "running"}

@app.websocket("/ws/{session_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, player_id: str):
    """ Establish a WebSocket connection for real-time communication.

    Args:
        websocket (WebSocket): The WebSocket connection
        session_id (str): The ID of the session to join
        player_id (str): The ID of the player joining the session

    Raises:
        HTTPException: If the session or player does not exist
    
    """
    # Validate session and player and close connection if invalid
    if session_id not in sessions or player_id not in players:
        await websocket.close(code=1008)
        print(f"Invalid session {session_id} or player {player_id}")
        return


    # Accept the WebSocket connection and broadcast join event to session
    await manager.connect(session_id, player_id, websocket)
    current_session = sessions[session_id]
    await manager.broadcast_to_session(
        session_id,
        {
            "event": "player_joined",
            "data": current_session.model_dump(),
        },
    )

    # Listen for incoming messages from the client and handles disconnections
    try:
        while True:
            # We can listen if players send messages too
            data = await websocket.receive_json()
            print(f"Received from {player_id}: {data}")
            await current_session.current_game.handle_action(data)
    except WebSocketDisconnect:
        print(f"❌ {player_id} disconnected from game {session_id}")
        await leave_game(session_id, LeaveSessionRequest(player_id=player_id))

    


@app.post("/session/create")
def create_session(entered_name: CreateJoinSessionRequest):
    """ Create a new game session with a leader player
    Args:
        entered_name (CreateJoinSessionRequest): The name of the player creating the session
    Raises:
        HTTPException: If the name is blank
    """

    if len(entered_name.name) == 0:
        raise HTTPException(status_code=400, detail="Blank name not allowed")
    
    """Create a new game room"""
    new_session_id = str(uuid.uuid4())[:8]
    new_player_id = str(uuid.uuid4())[:8]
    player = Player(
        player_id = new_player_id,
        name = entered_name.name,
    )
    
    players[new_player_id] = player

    # Create session and add leader player
    new_session = Session(
        session_id = new_session_id,
        leader = player
    )
    new_session.players.append(player)
    
    sessions[new_session_id] = new_session

    # Return session info including player ID
    response = dict(new_session.model_dump())
    response["you"] = new_player_id
    print(f"Created session {new_session_id} with player {new_player_id}")

    return response

@app.post("/session/{session_id}/join")
def join_game(session_id: str, entered_name: CreateJoinSessionRequest):
    """ Join an existing game session as a new player.
    
    Args:
        session_id (str): The ID of the session to join
        entered_name (CreateJoinSessionRequest): The name of the player joining the session
    Raises:
        HTTPException: If the session does not exist, is full, or the name is blank

    """

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]
    
    if len(session.players) >= 10:
        raise HTTPException(status_code=400, detail="Game is full")
    
    if len(entered_name.name) == 0:
        raise HTTPException(status_code=400, detail="Blank name not allowed")
    
    # Create new player and add to session
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
    """ Leave a game session.

    Args:
        session_id (str): The ID of the session to leave
        leaveReq (LeaveSessionRequest): The player ID of the player leaving the session

    Raises:
        HTTPException: If the session or player does not exist
    """

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]

    player_id = leaveReq.player_id
    if player_id not in players:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player = players[player_id]

    # Remove player from session and current game if active
    await session.leave(player)
    del players[player_id]
    await manager.disconnect(session_id, player_id)

    # Notify remaining players if session has > 2 players or session still has lobby leader in lobby
    if len(session.players) > 1 or (len(session.players) == 1 and not session.active_game() and (player_id != session.leader.player_id)):
        await manager.broadcast_to_session(
            session_id,
            {
                "event": "player_left",
                "data": session.model_dump(),
            },
        )
    else:
        # Otherwise close session and notify remaining players
        for remaining_player in session.players:
            await session.leave(remaining_player)
            await manager.broadcast_to_player(
                remaining_player.player_id,
                {
                    "event": "session_end",
                    "data": {
                        "message": "Not enough players!"
                    }
                } 
            )

            await manager.disconnect(session.session_id, remaining_player.player_id)
            del players[remaining_player.player_id]
            
        del sessions[session_id]
    
    return {"status": "success", "message": "game left"}
    

    
@app.post("/session/{session_id}/start")
async def start_game(session_id: str, player_id: str):
    """Start the game
    Args:
        session_id (str): The ID of the session to start
        player_id (str): The ID of the player requesting the start
    Raises:
        HTTPException: If the session does not exist, has insufficient players, the requester is not the leader, or a game is already in progress
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]
    if len(session.players) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")
    if session.leader.player_id != player_id:
        raise HTTPException(status_code=400, detail="Only lobby leader can start")
    if session.active_game() != False:
        raise HTTPException(status_code=403, detail="Game in progress")
    
    # Create new game instance and start it up
    new_game_id = str(uuid.uuid4())[:8]
    game = Game(
        game_id=new_game_id,
        session_id=session_id,
        players=session.players,
    )

    session.current_game = game
    await game.startup()
    
    return {"status": "success", "message": "game created"}

@app.get("/session/{session_id}")
async def get_game(session_id: str):
    """Gets the session state.
    
    Args:
        session_id (str): The ID of the session to get
    Raises:
        HTTPException: If the session does not exist
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Game not found")
    
    session = sessions[session_id]
    
    return {"event": "session_update", "data": session.model_dump()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
