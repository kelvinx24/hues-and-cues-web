import asyncio
from abc import ABC, abstractmethod
from pydantic import BaseModel
from connection_manager import manager

class Phase(ABC):
    def __init__(self, game: "Game", duration: int = 0):
        self.game = game
        self.duration = duration
        self.started = False
        self.ended = False

    @property
    def name(self):
        return self.__class__.__name__.replace("Phase", "").lower()

    async def start(self):
        if not self.started:
            await self._start_phase()
            self.started = True

    @abstractmethod
    async def _start_phase(self):
        pass

    @abstractmethod
    async def handle_event(self, sender: str, event: str, data: dict):
        pass

    async def end(self):
        if not self.end:  # and self.end_phase:
            await self._end_phase()
            self.ended = True

    # TODO: In the future, add support for factories creating next phases.
    # instead of one field holding current phase, we can hold a list of next phases as well.
    @abstractmethod
    async def _end_phase(self):
        pass


class StartUpPhase(Phase):
    def __init__(self, game, duration=0):
        super().__init__(game, 5)

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        pass

    async def _end_phase(self):
        await self.game._start_phase(HintingPhase(self.game))


class HintingPhase(Phase):
    def __init__(self, game, duration=0):
        super().__init__(game, 30)

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        if self.game.current_player == sender and event == "give_hint":
            self.game.hints.append(data["hint"])

    async def _end_phase(self):
        await self.game.set_phase(GuessingPhase(self.game))

class Guess(BaseModel):
    player_id: str
    position: tuple  # (row, col)

class GuessingPhase(Phase):
    def __init__(self, game, duration=0):
        super().__init__(game, 60)

    async def _start_phase(self):
        pass

    async def handle_event(self, sender, event, data):
        if self.game.current_player != sender and event == "make_guess":
            # guess logic
            self.game.player_guesses[sender] = data["guess"]
            guess = Guess(
                player_id=sender,
                position=data["guess"]
            )
            self.game.guesses.append(guess)
            if self.all_players_guessed():
                await self.end()

    async def _end_phase(self):
        await self.game.set_phase(ChoicePhase(self.game))

    def all_players_guessed(self):
        return len(self.game.player_guesses) == len(self.game.players) - 1


class ChoicePhase(Phase):
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
            self.game.player_guesses.clear()
            await self.game.set_phase(HintingPhase(self.game))


class ScorePhase(Phase):
    def __init__(self, game, duration=0):
        super().__init__(game, 5)

    async def _start_phase(self):
        self.calculate_scores()

    async def handle_action(self, sender, event, data):
        pass

    async def _end_phase(self):
        await self.game.set_phase(HintingPhase(self.game))

    def calculate_scores(self):
        for player, score in self.game.player_scores:
            self.game.player_scores[player.player_id] = score + 1
