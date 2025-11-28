import asyncio
import random
from pydantic import BaseModel, PrivateAttr
from typing import List, Optional
from player import Player
from connection_manager import manager
from phase import Phase, HintingPhase, Guess, StartUpPhase, NonePhase

class PlayerData(BaseModel):
    """ Data specific to a player within a game.
    
    Attributes:
        player (Player): The player this data belongs to.
        score (int): The player's current score.
        guess (tuple): The player's current guess (row, col) or None if not guessed yet.
    """
    player: Player
    score: int = 0
    guess: tuple = None


class Game(BaseModel):
    """ Game model representing the state and logic of a Hues and Cues game.
    
    Attributes:
        game_id (str): Unique identifier for the game.
        session_id (str): The ID of the session this game belongs to.
        is_over (bool): Indicates if the game is over.
        players (List[Player]): List of players participating in the game.
        target_color (Optional[tuple]): The target color for the current round (row, col).
        current_player (Optional[str]): The player ID of the current player.
        player_data (dict[str, PlayerData]): Mapping of player IDs to their game-specific data.
        hints (List[str]): List of hints given in the current round.
        guesses (List[Guess]): List of guesses made in the current round.
        _phase (Optional[Phase]): The current phase of the game (internal use).
        _timer_task (Optional[asyncio.Task]): The task managing the phase timer (internal use).
        phase_time_remaining (int): Time remaining in the current phase.
        current_round (int): The current round number.
        total_rounds (int): Total number of rounds in the game.
        colors (List[List]): The color grid used in the game.
    """
    game_id: str
    session_id: str
    is_over: bool = False
    players: List[Player] = []
    target_color: Optional[tuple] = None
    current_player: Optional[str] = None
    player_data: dict[str, PlayerData] = {}
    hints: List[str] = []
    guesses: List[Guess] = []
    _phase: Optional[Phase] = PrivateAttr(default=None)
    _timer_task: Optional[asyncio.Task] = PrivateAttr(default=None)
    phase_time_remaining: int = 0
    current_round: int = 0
    total_rounds: int = 3
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
        """Initialize and start the game.

        Sets up initial game state, assigns target color and current player,
        initializes player data, and starts the first phase.
        
        """
        self.target_color = self.generate_random_color()
        self.current_player = self.generate_random_player()
        for p in self.players:
            self.player_data[p.player_id] = PlayerData(
                player=p
            )

        self._phase = StartUpPhase(self)


        await manager.broadcast_game_state(self, "game_start", exclude_colors=False)

        await self.set_phase(StartUpPhase(self))

    def generate_random_color(self):
        """Generate a random color from the color grid.
        
        Returns:
            tuple: A tuple representing the (row, col) of the random color.
        """
        row = random.randint(0, len(self.colors) - 1)
        col = random.randint(0, len(self.colors[0]) - 1)
        random_color = (row, col)
        return random_color
    
    def generate_random_player(self, exclude=None):
        """Generate a random player ID from the list of players, excluding a specific player if provided.
        
        Args:
            exclude (str, optional): Player ID to exclude from selection. Defaults to None.
        
        Returns:
            str: The player ID of the randomly selected player.
        """
        choices = [p for p in self.players if p.player_id != exclude]
        return random.choice(choices).player_id


    async def set_phase(self, phase):
        """Set the current phase of the game.
        Args:
            phase (Phase): The new phase to set.
        """

        # Cancel the existing timer task if running
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

        # Sets the new phase and starts its timer if applicable
        self._phase = phase
        await manager.broadcast_game_state(self)

        if phase.duration > 0:
            self._timer_task = asyncio.create_task(self.run_phase_timer(phase.duration))
        
        await phase.start()
        await manager.broadcast_game_state(self)

    async def run_phase_timer(self, duration: int):
        """Run countdown timer for the current phase, broadcasting each second."""

        self.phase_time_remaining = duration

        while self.phase_time_remaining > 0:
            # Broadcast remaining time to all players
            await manager.broadcast_game_state(self)

            await asyncio.sleep(1)
            self.phase_time_remaining -= 1

        # When timer hits zero
        await manager.broadcast_game_state(self)

        # End the current phase
        if self._phase:
            print("TIMER ENDING")
            await self._phase.end()

    async def handle_action(self, body: dict):
        """ Handle an action within the game context.
        Args:
            body (dict): The action data containing event and associated data.
        """

        player_id = body.get("player_id")
        event = body.get("event")
        data = body.get("data", {})

        if (event == "request_game_state"):
            await manager.broadcast_game_state(self, exclude_colors=False)
            return


        # Delegate an action to the active phase.
        await self._phase.handle_event(player_id, event, data)
        await manager.broadcast_game_state(self)

    async def leave(self, player: Player):
        """ Remove a player from the game.

        Args:
            player (Player): The player to remove from the game.

        Returns:
            bool: True if the player was removed, False otherwise.
        """
        if player not in self.players:
            return False
        
        # If removing the player would leave 2 or fewer players, end the game
        if len(self.players) <= 2:
            self.is_over = True
            self.clear_game()
            return True
        
        # If the game is still ongoing, handle player removal based on current phase and player turn
        if not self.is_over:
            # if the player leaving is the current player, reset the round
            if player.player_id == self.current_player:
                self.reset_round()
                self.players.remove(player)
                del self.player_data[player.player_id]
                await self.set_phase(HintingPhase(self))
            else:
                self.players.remove(player)
                del self.player_data[player.player_id]
                await manager.broadcast_game_state(self)

            return True

    def reset_round(self):
        """ Reset the current round state, selecting a new current player and target color,
            and clearing hints and guesses.
        """
        self.current_player = self.generate_random_player(
            exclude=self.current_player
        )
        self.target_color = self.generate_random_color()
        self.guesses.clear()
        self.hints.clear()

        for id, pd in self.player_data.items():
            pd.guess = None

    def clear_game(self):
        """ Clear the game state when the game ends.
        """
        self.players.clear()
        self.player_data.clear()
        self.guesses.clear()
        self.hints.clear()
        self._phase = NonePhase(self)
        self.phase_time_remaining = 0

    async def end_game(self):
        """ End the game and notify all players.
        """
        self.is_over = True
        await manager.broadcast_game_state(self, "game_end")
        

    def to_dict(self, for_player_id: Optional[str] = None, exclude_colors=True) -> dict:
        """Return a JSON-safe dict representation of the game for a specific player.
        
        Args:
            for_player_id (Optional[str], optional): The player ID for whom the data is tailored
            exclude_colors (bool, optional): Whether to exclude color information from the output. Defaults to True.    
        Returns:
            dict: The dictionary representation of the game.
        """

        # Serialize all base data
        game_dict = self.model_dump(exclude_none=True)

        # Remove internal/non-serializable data
        if self._phase and not isinstance(self._phase, str):
            game_dict["current_phase"] = self._phase.name

        # Hide target color for all except the current player
        if (self._phase.name != "score") and (for_player_id is None or for_player_id != self.current_player):
            game_dict.pop("target_color", None)

        if exclude_colors:
            game_dict.pop("colors", None)

        return game_dict
    
    