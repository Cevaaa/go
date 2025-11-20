from __future__ import annotations
from .game import Game
from .models import PlayerColor, Piece, Position, Move, GameError
from .rules import is_five_in_a_row

class GomokuGame(Game):
    def __init__(self, size: int):
        super().__init__(size)

    def is_legal(self, move: Move) -> bool:
        if move.pass_move or move.resign:
            return False
        if move.pos is None:
            return False
        p = move.pos
        if not self.board.in_bounds(p):
            return False
        if not self.board.is_empty(p):
            return False
        return True

    def apply_move(self, move: Move):
        p = move.pos
        piece = Piece.from_player(move.player)
        self.board.set(p, piece)
        self.last_pos = p
        # Check end
        if is_five_in_a_row(self.board, p, piece):
            self.ended = True
            self._winner = move.player
        else:
            # Check draw
            full = all(self.board.grid[r][c] != Piece.EMPTY for r in range(self.board.size) for c in range(self.board.size))
            if full:
                self.ended = True
                self._winner = None
        # Switch
        if not self.ended:
            self.current = PlayerColor.WHITE if self.current == PlayerColor.BLACK else PlayerColor.BLACK