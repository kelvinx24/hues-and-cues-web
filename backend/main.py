from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import random
import uuid

app = FastAPI(title="Hues and Cues Game API")

# CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Game state storage (in-memory for simplicity)
games: Dict[str, dict] = {}
players: Dict[str, dict] = {}

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

class Player(BaseModel):
    name: str
    
class Game(BaseModel):
    game_id: str
    players: List[dict]
    target_color: Optional[tuple] = None
    current_player: Optional[str] = None
    guesses: List[dict] = []
    status: str = "waiting"  # waiting, playing, finished
    phase: str = "hinting"  # hinting, guessing, end_round
    guessing_timer_start: Optional[float] = None

class Guess(BaseModel):
    player_id: str
    color_position: tuple  # (row, col)

class Clue(BaseModel):
    player_id: str
    clue_text: str

@app.get("/")
def read_root():
    return {"message": "Hues and Cues Game API", "status": "running"}

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
        "target_color": None,
        "current_player": None,
        "guesses": [],
        "clues": [],
        "status": "waiting",
        "scores": {player_id: 0},
        "phase": "hinting",
        "guessing_timer_start": None,
        "players_who_guessed": []
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
def start_game(game_id: str, player_id: str):
    """Start the game"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if len(game["players"]) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players")
    
    # Pick random target color
    row = random.randint(0, len(COLORS) - 1)
    col = random.randint(0, len(COLORS[0]) - 1)
    game["target_color"] = (row, col)
    
    # Pick random starting player
    game["current_player"] = random.choice(game["players"])["id"]
    game["status"] = "playing"
    game["phase"] = "hinting"
    game["guessing_timer_start"] = None
    game["players_who_guessed"] = []
    
    return {"message": "Game started", "current_player": game["current_player"]}

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
        "phase": game.get("phase", "hinting"),
        "guessing_timer_start": game.get("guessing_timer_start"),
        "players_who_guessed": game.get("players_who_guessed", [])
    }
    
    # Only show target color to current player
    if player_id == game["current_player"]:
        response["target_color"] = game["target_color"]
    
    return response

@app.post("/game/{game_id}/clue")
def give_clue(game_id: str, clue: Clue):
    """Current player gives a clue"""
    import time
    
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if clue.player_id != game["current_player"]:
        raise HTTPException(status_code=403, detail="Not your turn")
    
    # Only allow clues during hinting phase
    if game.get("phase") != "hinting":
        raise HTTPException(status_code=400, detail="Can only give clues during hinting phase")
    
    game["clues"].append({
        "player_id": clue.player_id,
        "player_name": players[clue.player_id]["name"],
        "clue_text": clue.clue_text
    })
    
    # Transition to guessing phase
    game["phase"] = "guessing"
    game["guessing_timer_start"] = time.time()
    game["players_who_guessed"] = []
    
    return {"message": "Clue added, entering guessing phase"}

@app.post("/game/{game_id}/guess")
def make_guess(game_id: str, guess: Guess):
    """Make a guess for the target color"""
    import time
    
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if game["status"] != "playing":
        raise HTTPException(status_code=400, detail="Game is not in playing state")
    
    # Only allow guesses during guessing phase
    if game.get("phase") != "guessing":
        raise HTTPException(status_code=400, detail="Can only guess during guessing phase")
    
    # Current player cannot guess
    if guess.player_id == game["current_player"]:
        raise HTTPException(status_code=403, detail="Current player cannot guess")
    
    # Check if player already guessed this round
    if guess.player_id in game.get("players_who_guessed", []):
        raise HTTPException(status_code=400, detail="You have already guessed this round")
    
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
    
    # Mark player as having guessed
    if "players_who_guessed" not in game:
        game["players_who_guessed"] = []
    game["players_who_guessed"].append(guess.player_id)
    
    # Check if all other players have guessed (excluding current player)
    other_players = [p["id"] for p in game["players"] if p["id"] != game["current_player"]]
    all_guessed = all(p_id in game["players_who_guessed"] for p_id in other_players)
    
    # Check if timer has expired (60 seconds)
    timer_expired = False
    if game.get("guessing_timer_start"):
        elapsed = time.time() - game["guessing_timer_start"]
        timer_expired = elapsed >= 60
    
    # If all players guessed or timer expired, transition to end_round phase
    if all_guessed or timer_expired:
        game["phase"] = "end_round"
    
    return {
        "correct": distance == 0,
        "distance": distance,
        "message": f"Distance: {distance}" if distance > 0 else "Correct!",
        "phase": game["phase"]
    }

@app.post("/game/{game_id}/continue_round")
def continue_round(game_id: str, player_id: str):
    """Current player continues the round with another hint"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if player_id != game["current_player"]:
        raise HTTPException(status_code=403, detail="Only current player can continue round")
    
    if game.get("phase") != "end_round":
        raise HTTPException(status_code=400, detail="Can only continue during end_round phase")
    
    # Transition back to hinting phase
    game["phase"] = "hinting"
    game["guessing_timer_start"] = None
    game["players_who_guessed"] = []
    
    return {"message": "Round continues, you can give another hint"}

@app.post("/game/{game_id}/end_round")
def end_round(game_id: str, player_id: str):
    """Current player ends the round, scores and starts new round"""
    if game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")
    
    game = games[game_id]
    
    if player_id != game["current_player"]:
        raise HTTPException(status_code=403, detail="Only current player can end round")
    
    if game.get("phase") != "end_round":
        raise HTTPException(status_code=400, detail="Can only end round during end_round phase")
    
    target_row, target_col = game["target_color"]
    
    # Score the guesses - award points for closest guesses
    if game["guesses"]:
        # Sort guesses by distance
        sorted_guesses = sorted(game["guesses"], key=lambda g: g["distance"])
        
        # Award points based on accuracy
        for i, g in enumerate(sorted_guesses[:3]):  # Top 3 guesses
            if g["distance"] == 0:
                game["scores"][g["player_id"]] += 5
                game["scores"][game["current_player"]] += 3
            elif i == 0 and g["distance"] <= 2:  # Closest guess within 2
                game["scores"][g["player_id"]] += 3
            elif i == 1 and g["distance"] <= 3:  # Second closest within 3
                game["scores"][g["player_id"]] += 1
    
    # Move to next player
    current_player_index = next(
        (i for i, p in enumerate(game["players"]) if p["id"] == game["current_player"]),
        0
    )
    next_player_index = (current_player_index + 1) % len(game["players"])
    previous_player = game["current_player"]
    game["current_player"] = game["players"][next_player_index]["id"]
    
    # Pick new target color
    row = random.randint(0, len(COLORS) - 1)
    col = random.randint(0, len(COLORS[0]) - 1)
    previous_color = game["target_color"]
    game["target_color"] = (row, col)
    
    # Clear guesses and clues for new round
    game["guesses"] = []
    game["clues"] = []
    game["players_who_guessed"] = []
    
    # Reset to hinting phase
    game["phase"] = "hinting"
    game["guessing_timer_start"] = None
    
    return {
        "message": "Round ended, starting new round",
        "previous_color": previous_color,
        "previous_player": previous_player,
        "current_player": game["current_player"]
    }

@app.get("/colors")
def get_colors():
    """Get the color board"""
    return {"colors": COLORS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
