from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict
from player import Player

class State(str, Enum):
    WAITING: str = "waiting"
    PLAYING: str = "playing"
    FINISHED: str = "finished"

class Phase(str, Enum):
    HINTING: str = "hinting"
    GUESSING: str = "guessing"
    CHOICE: str = "choosing"
    ENDROUND: str = "ending"

class Game(BaseModel):
    game_id: str
    players: List[Player] = []
    target_color: Optional[tuple] = None
    current_player: Optional[str] = None
    player_data:  Dict = {}
    guesses: List[dict] = []
    status: State = State.PLAYING
    phase: Phase = Phase.HINTING

    