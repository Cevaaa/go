from __future__ import annotations
import math
import random
from typing import Optional, List, Tuple
from core.models import Position, PlayerColor, Piece
from .base import BaseAI

# 经典 8x8 权重，有利角/边，惩罚角旁边
WEIGHTS_8 = [
    [100, -20,  10,  5,  5, 10, -20, 100],
    [-20, -50,  -2, -2, -2, -2, -50, -20],
    [ 10,  -2,   1,  1,  1,  1,  -2,  10],
    [  5,  -2,   1,  0,  0,  1,  -2,   5],
    [  5,  -2,   1,  0,  0,  1,  -2,   5],
    [ 10,  -2,   1,  1,  1,  1,  -2,  10],
    [-20, -50,  -2, -2, -2, -2, -50, -20],
    [100, -20,  10,  5,  5, 10, -20, 100],
]

DIR8 = [(-1,-1), (-1,0), (-1,1),
        (0,-1),          (0,1),
        (1,-1),  (1,0),  (1,1)]

class HeuristicReversiAI(BaseAI):
    """黑白棋启发式AI：位置权重 + α * 可翻子数，角点优先。"""
    def __init__(self, alpha: float = 0.1):
        self.alpha = alpha

    def select_move(self, game) -> Optional[Position]:
        if not hasattr(game, "legal_moves"):
            return None
        legal = list(game.legal_moves())
        if not legal:
            return None
        # 评估每个合法步
        best = []
        best_score = -math.inf
        for pos in legal:
            s = self._score_move(game, pos)
            if s > best_score:
                best_score = s
                best = [pos]
            elif s == best_score:
                best.append(pos)
        return random.choice(best)

    def _score_move(self, game, pos: Position) -> float:
        board = game.board
        size = board.size
        r, c = pos.row, pos.col
        w = self._weight_at(size, r, c)
        flips = self._flip_count_if_place(game, pos)
        return w + self.alpha * flips

    def _weight_at(self, size: int, r: int, c: int) -> float:
        # 对非8x8：按边界映射近似采样
        if size == 8:
            return WEIGHTS_8[r][c]
        # 将坐标映射到 0..7
        rr = int(round((r / max(1, size-1)) * 7))
        cc = int(round((c / max(1, size-1)) * 7))
        rr = max(0, min(7, rr))
        cc = max(0, min(7, cc))
        return WEIGHTS_8[rr][cc]

    def _flip_count_if_place(self, game, pos: Position) -> int:
        # 仿照 ReversiGame._captures_in_dir 逻辑统计翻子数
        me = Piece.BLACK if game.current == PlayerColor.BLACK else Piece.WHITE
        opp = Piece.WHITE if me == Piece.BLACK else Piece.BLACK
        size = game.board.size
        total = 0
        for dr, dc in DIR8:
            r, c = pos.row + dr, pos.col + dc
            buf = 0
            while 0 <= r < size and 0 <= c < size:
                piece = game.board.grid[r][c]
                if piece == opp:
                    buf += 1
                    r += dr
                    c += dc
                    continue
                if piece == me:
                    total += buf
                break
        return total