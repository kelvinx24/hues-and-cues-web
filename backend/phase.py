from abc import ABC, abstractmethod
from pydantic import BaseModel
from player import Player

class Phase(ABC):
    """ Abstract base class for game phases.
    Attributes:
        game (Game): The game instance this phase belongs to.
        duration (int): Duration of the phase in seconds.
        started (bool): Whether the phase has started.
        ended (bool): Whether the phase has ended.
    """
    def __init__(self, game: "Game", duration: int = 0):
        self.game = game
        self.duration = duration
        self.started = False
        self.ended = False

    @property
    def name(self):
        """Return the name of the phase in lowercase without the 'Phase' suffix."""
        return self.__class__.__name__.replace("Phase", "").lower()

    async def start(self):
        """Start the phase if it hasn't been started yet."""
        if not self.started:
            await self._start_phase()
            self.started = True

    @abstractmethod
    async def _start_phase(self):
        """Perform phase-specific startup actions."""
        pass

    @abstractmethod
    async def handle_event(self, sender: str, event: str, data: dict):
        """Handle an event during the phase."""
        pass

    async def end(self):
        """End the phase if it hasn't been ended yet."""
        if not self.ended:
            await self._end_phase()
            self.ended = True

    # TODO: In the future, add support for factories creating next phases.
    # instead of one field holding current phase, we can hold a list of next phases as well.
    @abstractmethod
    async def _end_phase(self):
        """Perform phase-specific cleanup actions."""
        pass


class StartUpPhase(Phase):
    """Phase representing the startup of the game with a set duration."""
    def __init__(self, game, duration=0):
        super().__init__(game, 5)

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        pass

    async def _end_phase(self):
        await self.game.set_phase(HintingPhase(self.game))


class HintingPhase(Phase):
    """Phase where the current player give hints about the target color."""
    def __init__(self, game, duration=0):
        super().__init__(game, 30)

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        if self.game.current_player == sender and event == "give_hint":
            self.game.hints.append(data["hint"])
            await self.end()

    async def _end_phase(self):
        await self.game.set_phase(GuessingPhase(self.game))

class Guess(BaseModel):
    """ Model representing a player's guess.
    Attributes:
        player (Player): The player making the guess.
        position (tuple): The (row, col) position guessed by the player.
    """
    player: Player
    position: tuple  # (row, col)

class GuessingPhase(Phase):
    """Phase where non-current players make guesses about the target color."""

    def __init__(self, game, duration=0):
        super().__init__(game, 60)

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        if self.game.current_player != sender and event == "make_guess":
            # guess logic
            pos = (data.get("row"), data.get("col"))
            self.game.player_data[sender].guess = pos
            guess = Guess(
                player=self.game.player_data[sender].player,
                position=pos
            )
            self.game.guesses.append(guess)
            if self.all_players_guessed():
                await self.end()

    async def _end_phase(self):
        await self.game.set_phase(ChoicePhase(self.game))

    def all_players_guessed(self):
        count = 0
        for player, data in self.game.player_data.items():
            if data.guess is not None:
                count += 1

        return count == len(self.game.players) - 1 


class ChoicePhase(Phase):
    """Phase where the current player chooses to continue or end the round.

    Attributes:
        end_round (bool): Whether the round should end.
    """

    def __init__(self, game, duration=0):
        super().__init__(game, 30)
        self.end_round = False

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        if self.game.current_player == sender and event == "make_choice":
            if data["choice"] == "continue":
                self.end_round = False
                await self.end()
            elif data["choice"] == "end":
                self.end_round = True
                await self.end()
            else:
                pass

    async def _end_phase(self):
        if self.end_round:
            await self.game.set_phase(ScorePhase(self.game))
        else:
            for player,data in self.game.player_data.items():
                data.guess = None

            await self.game.set_phase(HintingPhase(self.game))

class NonePhase(Phase):
    """Phase representing no active phase (used when game is over)."""
    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        pass

    async def _end_phase(self):
        pass

class EndGamePhase(Phase):
    """Phase representing the end of the game."""
    def __init__(self, game, duration=0):
        super().__init__(game, 10)

    async def _start_phase(self):
        self.game.is_over = True

    async def handle_event(self, sender, event, data):
        pass

    async def _end_phase(self):
        await self.game.end_game()

class ScorePhase(Phase):
    """Phase where scores are calculated and awarded."""
    def __init__(self, game, duration=0):
        super().__init__(game, 5)

    async def _start_phase(self):
        self.calculate_scores()

    async def handle_event(self, sender, event, data):
        pass

    async def _end_phase(self):
        self.game.current_round += 1
        if self.game.current_round >= self.game.total_rounds:
            await self.game.set_phase(EndGamePhase(self.game))
        else:
            self.game.reset_round()
            await self.game.set_phase(HintingPhase(self.game))

    def calculate_scores(self):
        """
        Award points to all non-current players based on distance,
        then award bonus points to the current player based on correctness percentage.
        """

        # ----- Distance → Score lookup table -----
        # Edit here if you ever want to rebalance!
        distance_score = {
            0: 5,
            1: 3,
            2: 1,
            3: 1
        }

        total_score = 0
        current = self.game.current_player
        num_guessers = len(self.game.players) - 1
        max_score_per_player = 5

        current_color = self.game.target_color

        # ----- Score each non-current player -----
        for player, data in self.game.player_data.items():
            if player == current:
                continue
            
            # distance = max of the guess tuple/list
            guess = data.guess
            disX = abs(guess[0] - current_color[0])
            disY = abs(guess[1] - current_color[1])
            distance = max(disX, disY)

            # fallback to 0 if not in table
            give_score = distance_score.get(distance, 0)

            # apply
            self.game.player_data[player].score += give_score
            total_score += give_score

        # ----- Compute correctness percentage (0–1 range) -----
        max_total = num_guessers * max_score_per_player
        percent_correct = total_score / max_total if max_total else 0

        # ----- Award bonus to the current player -----
        if percent_correct == 1:
            bonus = 10
        elif percent_correct >= 0.5:
            bonus = 7
        elif percent_correct >= 0.25:
            bonus = 5
        elif percent_correct > 0:
            bonus = 3
        else:
            bonus = 0

        self.game.player_data[current].score += bonus

