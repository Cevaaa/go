from __future__ import annotations
from .gomoku import GomokuGame
from .go import GoGame

def normalize_game_type(game_type: str) -> str:
    """Normalize user/meta type to canonical id: 'go' or 'gomoku'."""
    gt = (game_type or "").strip().lower()
    if gt in ("go", "weiqi", "围棋"):
        return "go"
    if gt in ("gomoku", "五子棋", "gobang", "renju"):
        return "gomoku"
    # 兼容此前可能写入的类名
    if gt in ("gogame",):
        return "go"
    if gt in ("gomokugame",):
        return "gomoku"
    raise ValueError(f"未知游戏类型: {game_type}")

def create_game(game_type: str, size: int, komi: float = 7.5):
    canon = normalize_game_type(game_type)
    if canon == "gomoku":
        return GomokuGame(size)
    if canon == "go":
        return GoGame(size, komi=komi)
    # 理论不可达
    raise ValueError("未知游戏类型")