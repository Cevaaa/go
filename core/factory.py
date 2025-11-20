from __future__ import annotations
from typing import Union
from .gomoku import GomokuGame
from .go import GoGame

def create_game(game_type: str, size: int, komi: float = 7.5):
    gt = game_type.lower()
    if gt in ("gomoku", "五子棋"):
        return GomokuGame(size)
    if gt in ("go", "weiqi", "围棋"):
        return GoGame(size, komi=komi)
    raise ValueError("未知游戏类型")