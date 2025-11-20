from enum import Enum
from dataclasses import dataclass
from typing import Optional

class PlayerColor(Enum):
    BLACK = 1
    WHITE = 2

class Piece(Enum):
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    @staticmethod
    def from_player(p: PlayerColor):
        return Piece.BLACK if p == PlayerColor.BLACK else Piece.WHITE

    def to_player(self) -> Optional[PlayerColor]:
        if self == Piece.BLACK:
            return PlayerColor.BLACK
        if self == Piece.WHITE:
            return PlayerColor.WHITE
        return None

@dataclass(frozen=True)
class Position:
    row: int
    col: int

@dataclass
class Move:
    player: PlayerColor
    pos: Optional[Position] = None
    pass_move: bool = False
    resign: bool = False

class GameError(Exception):
    pass