from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import random
import uuid
from enum import Enum
import json
from connection_manager import ConnectionManager

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

# Game state storage (in-memory for simplicity)
games: Dict[str, dict] = {}
players: Dict[str, dict] = {}
connections: Dict[str, list] = {}


class State(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"

class Phase(Enum):
    HINTING = "hinting"
    GUESSING = "guessing"
    CHOICE = "choosing"
    ENDROUND = "ending"

class Player(BaseModel):
    name: str
    
class Game(BaseModel):
    game_id: str
    players: List[dict]
    lobby_leader: str = None
    target_color: Optional[tuple] = None
    current_player: Optional[str] = None
    player_last_guess:  Dict = {}
    guesses: List[dict] = []
    status: State = State.WAITING
    phase: Phase = Phase.HINTING

class Guess(BaseModel):
    player_id: str
    color_position: tuple  # (row, col)

class Clue(BaseModel):
    player_id: str
    clue_text: str

@app.get("/")
def read_root():
    return {"message": "Hues and Cues Game API", "status": "running"}


async def broadcast_to_game(game_id: str, message: dict):
    if game_id in connections:
        living_connections = []
        for ws in connections[game_id]:
            try:
                await ws.send_json(message)
                living_connections.append(ws)
            except Exception:
                # client probably disconnected
                continue
        connections[game_id] = living_connections


@app.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str, player_id: str):
    await websocket.accept()
    print(f"🔌 {player_id} connected to game {game_id}")

    if game_id not in connections:
        connections[game_id] = []
    connections[game_id].append(websocket)

    try:
        while True:
            # We can listen if players send messages too
            data = await websocket.receive_text()
            print(f"Received from {player_id}: {data}")
    except WebSocketDisconnect:
        print(f"❌ {player_id} disconnected from game {game_id}")
        connections[game_id].remove(websocket)


@app.post("/game/create")
def create_game(player: Player):
    """Create a new game room"""
    game_id = str(uuid.uuid4())[:8]
    player_id = str(uuid.uuid4())[:8]
    
    players[player_id] = {
        "id": player_id,
        "name": player.name,
        "game_id": game_id
    }
    
    games[game_id] = {
        "game_id": game_id,
        "players": [players[player_id]],
        "lobby_leader": player_id,
        "target_color": None,
        "current_player": None,
        "guesses": [],
        "clues": [],
        "status": State.WAITING,
        "phase": Phase.HINTING,
        "scores": {player_id: 0},
        "player_last_guess": {}
    }
    
    return {
        "game_id": game_id,
        "player_id": player_id,
        "player_name": player.name
    }

@app.post("/game/{game_id}/join")
def join_game(game_id: str, player: Player):
    """Join an existing game"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if len(game["players"]) >= 10:
        raise HTTPException(status_code=400, detail="Game is full")
    
    player_id = str(uuid.uuid4())[:8]
    players[player_id] = {
        "id": player_id,
        "name": player.name,
        "game_id": game_id
    }
    
    game["players"].append(players[player_id])
    game["scores"][player_id] = 0
    
    return {
        "game_id": game_id,
        "player_id": player_id,
        "player_name": player.name
    }


    
@app.post("/game/{game_id}/start")
async def start_game(game_id: str, player_id: str, background_tasks: BackgroundTasks = None):
    """Start the game"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    if len(game["players"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")
    if game["lobby_leader"] != player_id:
        raise HTTPException(status_code=400, detail="Only lobby leader can start")
    if game["status"] != State.WAITING:
        raise HTTPException(status_code=403, detail="Game in progress")
    
    # Pick random target color
    row = random.randint(0, len(COLORS) - 1)
    col = random.randint(0, len(COLORS[0]) - 1)
    game["target_color"] = (row, col)
    
    # Pick random starting player
    game["current_player"] = random.choice(game["players"])["id"]
    game["status"] = State.PLAYING
    game["phase"] = Phase.HINTING  # ✅ ensure phase is set
    
    # Broadcast game start to everyone
    if background_tasks is not None:
        background_tasks.add_task(
            broadcast_to_game,
            game_id,
            {
                "type": "game_phase_changed",
                "status": game["status"].value,
                "phase": game["phase"].value,
                "current_player": game["current_player"],
                "target_color": game["target_color"],
            }
        )
    
    startMes = {"message": "Game started", "current_player": game["current_player"]}
    
    return startMes

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
