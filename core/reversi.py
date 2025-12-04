from __future__ import annotations
from typing import List, Optional, Set, Tuple, Dict
from .game import Game
from .models import PlayerColor, Piece, Position, Move, GameError

DIR8 = [(-1,-1), (-1,0), (-1,1),
        (0,-1),          (0,1),
        (1,-1),  (1,0),  (1,1)]

class ReversiGame(Game):
    """
    Reversi / Othello implementation.
    Board uses Piece.EMPTY / Piece.BLACK / Piece.WHITE.
    Current player at start: BLACK. Initial four discs placed at center.
    """
    def __init__(self, size: int):
        super().__init__(size)
        self._init_start()

    def reset(self, size: int):
        super().reset(size)
        self._init_start()

    def _init_start(self):
        # Standard initial 4 discs centered
        s = self.board.size
        c1 = s//2 - 1
        c2 = s//2
        # Conventional: (c1,c1)=WHITE, (c2,c2)=WHITE, (c1,c2)=BLACK, (c2,c1)=BLACK
        self.board.set(Position(c1, c1), Piece.WHITE)
        self.board.set(Position(c2, c2), Piece.WHITE)
        self.board.set(Position(c1, c2), Piece.BLACK)
        self.board.set(Position(c2, c1), Piece.BLACK)
        self.current = PlayerColor.BLACK
        self.last_pos = None

    def _piece_of(self, player: PlayerColor) -> Piece:
        return Piece.BLACK if player == PlayerColor.BLACK else Piece.WHITE

    def _opponent_piece(self, player: PlayerColor) -> Piece:
        return Piece.WHITE if player == PlayerColor.BLACK else Piece.BLACK

    def _captures_in_dir(self, start: Position, dr: int, dc: int, player: PlayerColor) -> List[Position]:
        """
        From empty 'start', step (dr,dc). If first at least one opponent piece,
        and eventually a player's piece encountered with no gap, return list of
        opponent positions to flip; otherwise empty.
        """
        size = self.board.size
        r, c = start.row + dr, start.col + dc
        opp = self._opponent_piece(player)
        me = self._piece_of(player)
        buf: List[Position] = []
        while 0 <= r < size and 0 <= c < size:
            p = Position(r, c)
            piece = self.board.get(p)
            if piece == opp:
                buf.append(p)
                r += dr
                c += dc
                continue
            if piece == me:
                return buf if len(buf) > 0 else []
            # empty or edge
            return []
        return []

    def legal_moves(self) -> Set[Position]:
        res: Set[Position] = set()
        me = self._piece_of(self.current)
        size = self.board.size
        for r in range(size):
            for c in range(size):
                p = Position(r, c)
                if not self.board.is_empty(p):
                    continue
                flips_total = 0
                for dr, dc in DIR8:
                    flips = self._captures_in_dir(p, dr, dc, self.current)
                    if flips:
                        flips_total += len(flips)
                if flips_total > 0:
                    res.add(p)
        return res

    def is_legal(self, move: Move) -> bool:
        if move.resign:
            return True
        if move.pass_move:
            # Reversi has no "pass" action from user; skipping is forced when no legal moves.
            return False
        if move.pos is None:
            return False
        if move.player != self.current:
            return False
        p = move.pos
        if not self.board.in_bounds(p) or not self.board.is_empty(p):
            return False
        # must flip at least one direction
        for dr, dc in DIR8:
            if self._captures_in_dir(p, dr, dc, move.player):
                return True
        return False

    def apply_move(self, move: Move):
        if move.resign:
            self.ended = True
            self._winner = PlayerColor.WHITE if move.player == PlayerColor.BLACK else PlayerColor.BLACK
            return
        p = move.pos
        me = self._piece_of(move.player)
        flips: List[Position] = []
        for dr, dc in DIR8:
            flips.extend(self._captures_in_dir(p, dr, dc, move.player))
        if not flips:
            raise GameError("非法：该位置不能翻转任一对方棋子")
        # place and flip
        self.board.set(p, me)
        for q in flips:
            self.board.set(q, me)
        self.last_pos = p
        # switch turn
        self.current = PlayerColor.WHITE if self.current == PlayerColor.BLACK else PlayerColor.BLACK
        # end detection handled by controller (both no legal moves or board full)

    def count_discs(self) -> Dict[str, int]:
        size = self.board.size
        b = w = 0
        for r in range(size):
            for c in range(size):
                piece = self.board.grid[r][c]
                if piece == Piece.BLACK:
                    b += 1
                elif piece == Piece.WHITE:
                    w += 1
        return {"BLACK": b, "WHITE": w}