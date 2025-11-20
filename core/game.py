from __future__ import annotations
from typing import List, Optional, Dict, Any
from .models import PlayerColor, Piece, Position, Move, GameError
from .board import Board

class Game:
    def __init__(self, size: int):
        self.board = Board(size)
        self.current = PlayerColor.BLACK
        self.history: List[Dict[str, Any]] = []  # list of snapshots for undo
        self.ended: bool = False
        self._winner: Optional[PlayerColor] = None
        self.last_pos: Optional[Position] = None

    @property
    def winner(self):
        return self._winner

    def reset(self, size: int):
        self.board = Board(size)
        self.current = PlayerColor.BLACK
        self.history.clear()
        self.ended = False
        self._winner = None
        self.last_pos = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "board": self.board.to_array(),
            "current": self.current.value,
            "ended": self.ended,
            "winner": self._winner.value if self._winner else None,
            "last": (self.last_pos.row, self.last_pos.col) if self.last_pos else None,
        }

    def restore(self, snap: Dict[str, Any]):
        self.board = Board.from_array(snap["board"])
        self.current = PlayerColor(snap["current"])
        self.ended = snap["ended"]
        self._winner = PlayerColor(snap["winner"]) if snap["winner"] else None
        if snap["last"]:
            r, c = snap["last"]
            self.last_pos = Position(r, c)
        else:
            self.last_pos = None

    def is_legal(self, move: Move) -> bool:
        raise NotImplementedError

    def apply_move(self, move: Move):
        raise NotImplementedError

    def step(self, move: Move):
        if self.ended:
            raise GameError("对局已结束")
        if move.player != self.current:
            raise GameError("未到该方行棋")
        if not self.is_legal(move):
            raise GameError("不合法的落子/操作")
        self.history.append(self.snapshot())
        self.apply_move(move)

    def undo(self) -> bool:
        if not self.history:
            return False
        snap = self.history.pop()
        self.restore(snap)
        return True

    def serialize(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "board": self.board.to_array(),
            "current": self.current.value,
            "ended": self.ended,
            "winner": self._winner.value if self._winner else None,
            "last": (self.last_pos.row, self.last_pos.col) if self.last_pos else None,
        }

    def deserialize(self, data: Dict[str, Any]):
        self.board = Board.from_array(data["board"])
        self.current = PlayerColor(data["current"])
        self.ended = data["ended"]
        self._winner = PlayerColor(data["winner"]) if data["winner"] else None
        if data.get("last"):
            r, c = data["last"]
            self.last_pos = Position(r, c)
        else:
            self.last_pos = None

    def get_state(self) -> Dict[str, Any]:
        return {
            "board": self.board,
            "current": self.current,
            "ended": self.ended,
            "winner": self._winner,
            "last_pos": self.last_pos,
        }