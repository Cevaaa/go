from __future__ import annotations
from .gomoku import GomokuGame
from .go import GoGame
from .reversi import ReversiGame

def normalize_game_type(game_type: str) -> str:
    gt = (game_type or "").strip().lower()
    if gt in ("go", "weiqi", "围棋"):
        return "go"
    if gt in ("gomoku", "五子棋", "gobang", "renju"):
        return "gomoku"
    if gt in ("reversi", "othello", "黑白棋"):
        return "reversi"
    if gt in ("gogame",):
        return "go"
    if gt in ("gomokugame",):
        return "gomoku"
    if gt in ("reversigame",):
        return "reversi"
    raise ValueError(f"未知游戏类型: {game_type}")

def create_game(game_type: str, size: int, komi: float = 7.5):
    canon = normalize_game_type(game_type)
    if canon == "gomoku":
        return GomokuGame(size)
    if canon == "go":
        return GoGame(size, komi=komi)
    if canon == "reversi":
        return ReversiGame(size)
    raise ValueError("未知游戏类型")