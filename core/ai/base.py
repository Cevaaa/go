from __future__ import annotations
from typing import Optional, Set
from core.models import Position

class IGameAI:
    """通用AI接口：给定 game，返回选择的Position；无合法步时返回 None。"""
    def select_move(self, game) -> Optional[Position]:
        raise NotImplementedError

class BaseAI(IGameAI):
    """提供通用工具的AI基类。"""
    def select_move(self, game) -> Optional[Position]:
        raise NotImplementedError

    def _legal_moves(self, game) -> Set[Position]:
        # 仅针对实现了 legal_moves 的游戏（如 Reversi）
        if hasattr(game, "legal_moves"):
            return set(game.legal_moves())
        return set()