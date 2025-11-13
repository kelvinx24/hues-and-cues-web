from pydantic import BaseModel
from typing import List, Optional, Dict

class Player(BaseModel, frozen=True):
    player_id: str
    name: str