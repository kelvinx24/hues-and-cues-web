import asyncio
from enum import Enum
import random
from pydantic import BaseModel, PrivateAttr
from typing import List, Optional, Dict
from player import Player
from connection_manager import manager
from phase import Phase, HintingPhase, GuessingPhase, ChoicePhase, Guess

class State(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"

class PlayerData(BaseModel):
    player: Player
    score: int = 0
    guess: tuple = None


class Game(BaseModel):
    game_id: str
    session_id: str
    players: List[Player] = []
    target_color: Optional[tuple] = None
    current_player: Optional[str] = None
    player_data: dict[str, PlayerData] = {}
    hints: List[str] = []
    guesses: List[Guess] = []
    status: State = State.PLAYING
    _phase: Optional[Phase] = PrivateAttr(default=None)
    phase_time_remaining: int = 0
    colors: List[List] = [
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
    
    async def startup(self):
        self.target_color = self.generate_random_color()
        self.current_player = self.generate_random_player()
        for p in self.players:
            self.player_data[p.player_id] = PlayerData(
                player=p
            )

        self._phase = HintingPhase(self)

        await manager.broadcast_game_state(self, "game_start", exclude_colors=False)



    def generate_random_color(self):
        row = random.randint(0, len(self.colors) - 1)
        col = random.randint(0, len(self.colors[0]) - 1)
        random_color = (row, col)
        return random_color
    
    def generate_random_player(self):
        random_player = random.choice(self.players).player_id
        return random_player

    async def set_phase(self, phase):
        """Start a new phase, replacing the current one."""
        self._phase = phase
        await manager.broadcast_game_state(self)

        if phase.duration > 0:
            asyncio.create_task(self.run_phase_timer(phase.duration))
        # Start phase
        await phase.start()
        await manager.broadcast_game_state(self)

    async def run_phase_timer(self, duration: int):
        """Run countdown timer for the current phase, broadcasting each second."""

        self.phase_time_remaining = duration

        while self.phase_time_remaining > 0:
            # Broadcast remaining time to all players
            await manager.broadcast_to_session(self.session_id, {
                "event": "phase_timer_update",
                "time_remaining": self.phase_time_remaining
            })

            await asyncio.sleep(1)
            self.phase_time_remaining -= 1

        # When timer hits zero
        await manager.broadcast_to_session(self.session_id, {
            "event": "phase_timer_end",
            "phase": self._phase.name if self._phase else None
        })

        # End the current phase
        if self._phase:
            await self._phase.end()

    async def handle_action(self, body: dict):
        player_id = body.get("player_id")
        event = body.get("event")
        data = body.get("data", {})

        """Delegate an action to the active phase."""
        await self._phase.handle_event(player_id, event, data)
        await manager.broadcast_game_state(self)

    def to_dict(self, for_player_id: Optional[str] = None, exclude_colors=True) -> dict:
        """Return a JSON-safe dict representation of the game for a specific player."""

        # Serialize all base data
        game_dict = self.model_dump(exclude_none=True)

        # Remove internal/non-serializable data
        if self._phase and not isinstance(self._phase, str):
            game_dict["current_phase"] = self._phase.name

        # Hide target color for all except the current player
        if for_player_id is None or for_player_id != self.current_player:
            game_dict.pop("target_color", None)

        if exclude_colors:
            game_dict.pop("colors", None)

        return game_dict
    
    