from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict
from player import Player
from connection_manager import manager
from phase import Phase, HintingPhase, GuessingPhase, ChoicePhase

class State(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"




class Game(BaseModel):
    game_id: str
    session_id: str
    players: List[Player] = []
    target_color: Optional[tuple] = None
    current_player: Optional[str] = None
    player_scores:  dict[str, int] = {}
    player_guesses: dict[str, str] = {}
    hints: List[str] = []
    guesses: List[dict] = []
    status: State = State.PLAYING
    current_phase: Phase


    def __init__(self, game_id: str, players: list):
        self.game_id = game_id
        self.players = players
        self.phase = HintingPhase(self)
        self.phase_task = None

    async def set_phase(self, phase):
        """Start a new phase, replacing the current one."""
        self.phase = phase
        await manager.broadcast(self.game_id, {
            "event": "phase_start",
            "phase": phase.name
        })

        # Start phase
        phase.start()

    async def handle_action(self, body: dict):
        player_id = body["player_id"]
        event = body["event"]
        data = body.get("data", {})

        """Delegate an action to the active phase."""
        await self.phase.handle_event(player_id, event, data)