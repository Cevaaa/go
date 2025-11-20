from __future__ import annotations
from typing import List, Iterable
from .models import Piece, Position

class Board:
    def __init__(self, size: int):
        if size < 8 or size > 19:
            raise ValueError("棋盘大小需在 8~19 之间")
        self.size = size
        self.grid: List[List[Piece]] = [[Piece.EMPTY for _ in range(size)] for _ in range(size)]

    def clone(self) -> "Board":
        b = Board(self.size)
        for r in range(self.size):
            for c in range(self.size):
                b.grid[r][c] = self.grid[r][c]
        return b

    def in_bounds(self, p: Position) -> bool:
        return 0 <= p.row < self.size and 0 <= p.col < self.size

    def get(self, p: Position) -> Piece:
        return self.grid[p.row][p.col]

    def set(self, p: Position, piece: Piece):
        self.grid[p.row][p.col] = piece

    def is_empty(self, p: Position) -> bool:
        return self.get(p) == Piece.EMPTY

    def neighbors(self, p: Position) -> Iterable[Position]:
        dirs = [(-1,0),(1,0),(0,-1),(0,1)]
        for dr, dc in dirs:
            nr, nc = p.row + dr, p.col + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                yield Position(nr, nc)

    def to_array(self):
        return [[self.grid[r][c].value for c in range(self.size)] for r in range(self.size)]

    @staticmethod
    def from_array(arr) -> "Board":
        size = len(arr)
        b = Board(size)
        for r in range(size):
            for c in range(size):
                val = arr[r][c]
                b.grid[r][c] = Piece(val)
        return b