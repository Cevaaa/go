from __future__ import annotations
import random
from typing import Optional
from core.models import Position
from .base import BaseAI

class RandomReversiAI(BaseAI):
    """黑白棋随机AI：从合法集合中随机选择。"""
    def select_move(self, game) -> Optional[Position]:
        if not hasattr(game, "legal_moves"):
            return None
        moves = list(game.legal_moves())
        if not moves:
            return None
        return random.choice(moves)