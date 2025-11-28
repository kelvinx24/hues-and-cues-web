from pydantic import BaseModel

class Player(BaseModel, frozen=True):
    """ Player model representing a game participant.
    Attributes:
        player_id (str): Unique identifier for the player.
        name (str): Name of the player.
    """
    player_id: str
    name: str