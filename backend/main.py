from fastapi import FastAPI, Body, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Annotated, List, Optional, Dict
import random
import uuid

import json
from connection_manager import ConnectionManager

from player import Player
from game import State, Phase, Game

app = FastAPI(title="Hues and Cues Game API")
manager = ConnectionManager()

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Color board - 480 colors in a grid
COLORS = [
    # Reds
    ["#8B0000", "#A52A2A", "#B22222", "#DC143C", "#FF0000", "#FF6347", "#FF7F50", "#CD5C5C", "#F08080", "#E9967A"],
    # Oranges
    ["#FF4500", "#FF8C00", "#FFA500", "#FFB84D", "#FFC04D", "#FFD700", "#F0E68C", "#EEE8AA", "#FAFAD2", "#FFFFE0"],
    # Yellows
    ["#FFFF00", "#FFFF66", "#FFFF99", "#FFFFCC", "#FFFFE0", "#FFFACD", "#FFF8DC", "#FFEFD5", "#FFE4B5", "#FFDAB9"],
    # Greens
    ["#006400", "#228B22", "#32CD32", "#00FF00", "#7CFC00", "#ADFF2F", "#9ACD32", "#90EE90", "#98FB98", "#8FBC8F"],
    # Cyans
    ["#00CED1", "#00FFFF", "#E0FFFF", "#AFEEEE", "#7FFFD4", "#40E0D0", "#48D1CC", "#00CED1", "#5F9EA0", "#4682B4"],
    # Blues
    ["#000080", "#00008B", "#0000CD", "#0000FF", "#4169E1", "#6495ED", "#87CEEB", "#87CEFA", "#ADD8E6", "#B0C4DE"],
    # Purples
    ["#4B0082", "#483D8B", "#6A5ACD", "#7B68EE", "#9370DB", "#8A2BE2", "#9400D3", "#9932CC", "#BA55D3", "#DA70D6"],
    # Pinks
    ["#C71585", "#D02090", "#FF1493", "#FF69B4", "#FFB6C1", "#FFC0CB", "#FFE4E1", "#FFF0F5", "#FAE7E7", "#FADADD"],
    # Browns
    ["#8B4513", "#A0522D", "#D2691E", "#CD853F", "#F4A460", "#DEB887", "#D2B48C", "#BC8F8F", "#F5DEB3", "#FFE4C4"],
    # Grays
    ["#000000", "#2F4F4F", "#696969", "#808080", "#A9A9A9", "#C0C0C0", "#D3D3D3", "#DCDCDC", "#F5F5F5", "#FFFFFF"]
]


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

class Guess(BaseModel):
    player_id: str
    color_position: tuple  # (row, col)

class Clue(BaseModel):
    player_id: str
    clue_text: str

# Game state storage (in-memory for simplicity)
sessions: Dict[str, Session] = {}
players: Dict[str, Player] = {}
session_connections: Dict[str, List[WebSocket]] = {}
player_connections: Dict[str, WebSocket] = {}

@app.get("/")
def read_root():
    return {"message": "Hues and Cues Game API", "status": "running"}


async def broadcast_to_player(player_id: str, message: dict):
    if player_id in player_connections:
        ws = player_connections[player_id]
        try:
            await ws.send_json(message)
        except Exception as e:
            print(e)
            print("Could not send to player with id " + player_id)

async def broadcast_to_game(session_id: str, message: dict):

    if session_id in session_connections:
        living_connections = []
        for ws in session_connections[session_id]:
            try:
                await ws.send_json(message)
                living_connections.append(ws)
            except Exception:
                # client probably disconnected
                continue
        session_connections[session_id] = living_connections

async def broadcast_to_rest(session_id: str, message: dict):
    if session_id not in session_connections:
        return
    
    session = sessions[session_id]
    game = session.current_game
    if game is not None:
        for player in session.players:
            if player.player_id == game.current_player:
                continue

            await broadcast_to_player(player.player_id, message)

async def broadcast_to_current_player(session_id: str, message: dict):
    if session_id not in session_connections:
        return
    
    session = sessions[session_id]
    game = session.current_game
    if game is not None:
        await broadcast_to_player(game.current_player, message)
                



@app.websocket("/ws/{session_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, player_id: str):
    print("Active sessions:", list(sessions.keys()))
    print("Active players:", list(players.keys()))
    if session_id not in sessions or player_id not in players:
        await websocket.close(code=1008)
        print(f"Invalid session {session_id} or player {player_id}")
        return


    await websocket.accept()

    print(f"🔌 {player_id} connected to game {session_id}")
    if session_id not in session_connections:
        session_connections[session_id] = []

    
    session_connections[session_id].append(websocket)
    player_connections[player_id] = websocket

    print("Active session connections:", len(session_connections[session_id]))
    await broadcast_to_game(
        session_id,
        {
            "event": "player_joined",
            "data": sessions[session_id].model_dump(),
        },
    )

    try:
        while True:
            # We can listen if players send messages too
            data = await websocket.receive_text()
            print(f"Received from {player_id}: {data}")
    except WebSocketDisconnect:
        print(f"❌ {player_id} disconnected from game {session_id}")


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

    if player_id in player_connections:
        ws = player_connections.pop(player_id)
        await ws.close()
    
    await broadcast_to_game(
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
    row = random.randint(0, len(COLORS) - 1)
    col = random.randint(0, len(COLORS[0]) - 1)
    random_color = (row, col)
    
    # Pick random starting player
    random_player = random.choice(session.players).player_id

    new_game_id = str(uuid.uuid4())[:8]

    game = Game(
        game_id=new_game_id,
        players=session.players,
        target_color=random_color,
        current_player=random_player
    )

    session.current_game = game
    
    # Broadcast game start to everyone
    await broadcast_to_rest(
        session_id, 
        {
            "event": "game_start",
            "data": game.model_dump(exclude='target_color')
        } 
    )   

    await broadcast_to_current_player(
        session_id, 
        {
            "event": "game_start",
            "data": game.model_dump()
        }
    )
    return {"status": "success", "message": "game created"}

@app.get("/game/{game_id}")
def get_game(game_id: str, player_id: str):
    """Get game state"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    # Hide target color from non-current players
    response = {
        "game_id": game["game_id"],
        "players": game["players"],
        "current_player": game["current_player"],
        "guesses": game["guesses"],
        "clues": game["clues"],
        "status": game["status"],
        "scores": game["scores"],
        "phase": game["phase"],
        "last_guesses": game["player_last_guess"]
    }
    
    # Only show target color to current player
    if player_id == game["current_player"]:
        response["target_color"] = game["target_color"]
    
    return response

@app.post("/game/{game_id}/clue")
def give_clue(game_id: str, clue: Clue):
    """Current player gives a clue"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if clue.player_id != game["current_player"]:
        raise HTTPException(status_code=403, detail="Not your turn")
    
    if game["status"] != State.PLAYING:
        raise HTTPException(status_code=400, detail="Game is not in playing state")
    
    if game["phase"] != Phase.HINTING:
        raise HTTPException(status_code=403, detail="Not hinting phase")
    
    
    game["clues"].append({
        "player_id": clue.player_id,
        "player_name": players[clue.player_id]["name"],
        "clue_text": clue.clue_text
    })

    game["phase"] = Phase.GUESSING

    
    return {"message": "Clue added"}

@app.post("/game/{game_id}/continue_round")
def continue_round(game_id: str, player_id: str):
    """Make a choice after guessing phase"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if game["phase"] != Phase.CHOICE:
        raise HTTPException(status_code=400, detail="Game is not in playing state")
    
    if player_id != game["current_player"]:
        raise HTTPException(status_code=403, detail="Not your turn")
    
    game["phase"] = Phase.HINTING

    return {"message": "Round continues, give another hint"}

@app.post("/game/{game_id}/end_round")
def end_round(game_id: str, player_id: str):
    """Make a choice after guessing phase"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if player_id != game["current_player"]:
        raise HTTPException(status_code=403, detail="Not your turn")
    
    if game["status"] != State.PLAYING:
        raise HTTPException(status_code=400, detail="Game is not in playing state")
    
    if game["phase"] != Phase.CHOICE:
        raise HTTPException(status_code=403, detail="Not hinting phase")
    
    game = games[game_id]

    # Score players
    for player, distance in game["player_last_guess"].items():
        game["scores"][player] += distance


    game["scores"][game["current_player"]] += 3
    
    # Start a new round with a new color and next player
    current_player_index = next(
        (i for i, p in enumerate(game["players"]) if p["id"] == game["current_player"]),
        0
    )

    next_player_index = (current_player_index + 1) % len(game["players"])
    game["current_player"] = game["players"][next_player_index]["id"]

    prev_row, prev_col = game["target_color"]
    
    # Pick new target color
    row = random.randint(0, len(COLORS) - 1)
    col = random.randint(0, len(COLORS[0]) - 1)
    game["target_color"] = (row, col)
    
    # Clear guesses and clues for new round
    game["guesses"] = []
    game["clues"] = []
    game["player_last_guess"] = {}
    game["phase"] = Phase.ENDROUND

    return {
        "message": "End Round!",
        "target_color": (prev_row, prev_col),
        "next_player": game["current_player"]
    }



@app.post("/game/{game_id}/guess")
def make_guess(game_id: str, guess: Guess):
    """Make a guess for the target color"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if game["phase"] != Phase.GUESSING:
        raise HTTPException(status_code=400, detail="Game is not in playing state")
    
    row, col = guess.color_position
    target_row, target_col = game["target_color"]
    
    # Calculate distance from target
    distance = abs(row - target_row) + abs(col - target_col)

    game["guesses"].append({
        "player_id": guess.player_id,
        "player_name": players[guess.player_id]["name"],
        "position": guess.color_position,
        "distance": distance,
        "correct": distance == 0
    })

    game["player_last_guess"][guess.player_id] = distance

    if len(game["player_last_guess"]) == len(game["players"]) - 1:
        game["phase"] = Phase.CHOICE

    return {
        "phase": game["phase"].value,
        "guess_entered": True,
        "position": guess.color_position
    }

@app.get("/colors")
def get_colors():
    """Get the color board"""
    return {"colors": COLORS}




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
