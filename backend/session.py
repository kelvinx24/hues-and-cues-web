from typing import List, Optional

from pydantic import BaseModel
from backend.game import Game
from backend.player import Player
from connection_manager import manager


class Session(BaseModel):
    """ Session model representing a game session with players and an optional active game.
    
    Attributes:
        session_id (str): Unique identifier for the session.
        leader (Player): The player who created the session and is the leader.
        players (List[Player]): List of players currently in the session.
        current_game (Optional[Game]): The active game in the session, if any.
    """

    session_id: str
    leader: Player
    players: List[Player] = []
    current_game: Optional[Game] = None

    def active_game(self):
        """ Check if there is an active game in the session.
        """

        return self.current_game != None and not self.current_game.is_over
    
    def join(self, player: Player):
        """ Add a player to the session if no game is currently active.
        
        Args:
            player (Player): The player to add to the session.
        """

        if self.current_game is None:
            self.players.append(player)
            return True

        return False
    
    async def handle_action(self, body: dict):
        """ Handle an action within the session context.
        Args:
            body (dict): The action data containing event and associated data.
        """
        event = body.get("event")
        data = body.get("data", {})
        if event == "request_session_state":
            await manager.broadcast_to_session(
                self.session_id,
                {
                    "event": "session_update",
                    "data" : self.model_dump()
                }
            )
    
    async def leave(self, player: Player):
        """ Remove a player from the session and active game if applicable.
        
        Args:
            player (Player): The player to remove from the session.
        """
        if player in self.players:
            self.players.remove(player)
            if self.active_game():
                await self.current_game.leave(player)

            if player.player_id == self.leader.player_id:
                self.current_game = None