from __future__ import annotations
from typing import Optional, Tuple
import json
from core.models import PlayerColor, Move, Position, GameError
from core.factory import create_game, normalize_game_type
from .renderer import ImageRenderer

# AI
from core.ai.base import IGameAI
from core.ai.random_ai import RandomReversiAI
from core.ai.reversi_rule_ai import HeuristicReversiAI

class UIController:
    def __init__(self):
        self.game = None
        self.renderer = ImageRenderer()
        self.game_type = "围棋"
        self.size = 19
        self.komi = 7.5
        self.message = "Welcome to the Board Game Platform"
        self.theme = "wood"
        # AI 配置
        self.black_side = "玩家"  # or "AI"
        self.white_side = "玩家"  # or "AI"
        self.ai_kind = "Reversi"  # 预留扩展
        self.ai_level = 1         # 1: Random, 2: Heuristic
        self._ai_black: Optional[IGameAI] = None
        self._ai_white: Optional[IGameAI] = None

    def set_theme(self, theme: str):
        self.theme = theme
        self.renderer.set_theme(theme)

    def _build_ai(self, level: int) -> IGameAI:
        # 仅 Reversi 有效
        if level == 1:
            return RandomReversiAI()
        return HeuristicReversiAI(alpha=0.12)

    def _refresh_ai_agents(self):
        gt = normalize_game_type(self.game_type)
        if gt != "reversi":
            self._ai_black = None
            self._ai_white = None
            return
        self._ai_black = self._build_ai(self.ai_level) if self.black_side == "AI" else None
        self._ai_white = self._build_ai(self.ai_level) if self.white_side == "AI" else None

    def new_game(self, game_type: str, size: int, komi: float, black_side: str = "玩家", white_side: str = "玩家", ai_kind: str = "Reversi", ai_level: int = 1):
        if size < 8 or size > 19:
            raise GameError("棋盘大小需在 8~19 之间")
        self.game_type = game_type
        self.size = size
        self.komi = komi
        self.black_side = black_side
        self.white_side = white_side
        self.ai_kind = ai_kind
        self.ai_level = int(ai_level)
        self.game = create_game(game_type, size, komi)
        self._refresh_ai_agents()
        # 非 Reversi 的棋种不开启AI
        if normalize_game_type(game_type) != "reversi" and (self.black_side == "AI" or self.white_side == "AI"):
            self.black_side = "玩家"
            self.white_side = "玩家"
            self._ai_black = None
            self._ai_white = None
            self.message = "AI is only available for Reversi currently. Switched to PvP."
        else:
            self.message = f"New game: {game_type} {size}x{size}"
        # 新局后尝试让 AI 先手（如黑为AI）
        self._maybe_ai_play_loop()
        return self.get_image()

    def _turn_label(self):
        if not self.game:
            return ""
        if self.game.ended:
            if self.game_type.lower() in ("go","weiqi","围棋"):
                from core.go import GoGame
                if isinstance(self.game, GoGame):
                    score = self.game.score()
                    if score is not None:
                        b = score["BLACK"]
                        w = score["WHITE"]
                        if b > w:
                            return f"End: Black wins (B {b:.1f} : W {w:.1f}, komi {self.game.komi})"
                        elif w > b:
                            return f"End: White wins (B {b:.1f} : W {w:.1f}, komi {self.game.komi})"
                        else:
                            return f"End: Draw (B {b:.1f} : W {w:.1f})"
            if self.game.winner is None:
                return "End: Draw"
            else:
                return f"End: {'Black' if self.game.winner==PlayerColor.BLACK else 'White'} wins"
        else:
            return f"Turn: {'Black' if self.game.current==PlayerColor.BLACK else 'White'}"

    def get_image(self):
        if not self.game:
            return None
        text = f"{self.message} | {self._turn_label()}"
        return self.renderer.render(
            self.game.board, self.game_type, self.game.last_pos, text,
            None if getattr(self.game, "ended", False) else self.game.current
        )

    def _ended_popup(self) -> Optional[str]:
        if not self.game or not getattr(self.game, "ended", False):
            return None
        if self.game_type.lower() in ("go","weiqi","围棋"):
            from core.go import GoGame
            if isinstance(self.game, GoGame):
                score = self.game.score()
                if score is not None:
                    b = score["BLACK"]
                    w = score["WHITE"]
                    if b > w:
                        return "黑方胜利！请开启新对局。"
                    elif w > b:
                        return "白方胜利！请开启新对局。"
                    else:
                        return "平局！请开启新对局。"
        if self.game.winner is None:
            return "平局！请开启新对局。"
        else:
            return f"{'黑方' if self.game.winner==PlayerColor.BLACK else '白方'}胜利！请开启新对局。"

    # ------- Reversi 辅助：自动跳过/判终局 -------
    def _reversi_auto_skip_or_end(self):
        from core.reversi import ReversiGame
        if not isinstance(self.game, ReversiGame) or self.game.ended:
            return False
        moves_now = self.game.legal_moves()
        if moves_now:
            return False
        self.game.current = PlayerColor.WHITE if self.game.current == PlayerColor.BLACK else PlayerColor.BLACK
        self.message = "No legal move; turn skipped."
        moves_after = self.game.legal_moves()
        if not moves_after:
            counts = self.game.count_discs()
            b, w = counts["BLACK"], counts["WHITE"]
            self.game.ended = True
            if b > w:
                self.game._winner = PlayerColor.BLACK
            elif w > b:
                self.game._winner = PlayerColor.WHITE
            else:
                self.game._winner = None
        return True

    def _reversi_check_full_end(self):
        from core.reversi import ReversiGame
        if not isinstance(self.game, ReversiGame) or self.game.ended:
            return
        size = self.game.board.size
        full = True
        for r in range(size):
            for c in range(size):
                if self.game.board.grid[r][c].value == 0:
                    full = False
                    break
            if not full:
                break
        if full:
            counts = self.game.count_discs()
            b, w = counts["BLACK"], counts["WHITE"]
            self.game.ended = True
            if b > w:
                self.game._winner = PlayerColor.BLACK
            elif w > b:
                self.game._winner = PlayerColor.WHITE
            else:
                self.game._winner = None

    # ------- AI 回合循环 -------
    def _agent_for_current(self) -> Optional[IGameAI]:
        if normalize_game_type(self.game_type) != "reversi":
            return None
        if self.game.current == PlayerColor.BLACK:
            return self._ai_black
        else:
            return self._ai_white

    def _maybe_ai_play_once(self) -> bool:
        if not self.game or self.game.ended:
            return False
        # Reversi 开局/上一手后可能无合法步，先尝试跳过或终局
        if normalize_game_type(self.game_type) == "reversi":
            if self._reversi_auto_skip_or_end():
                return True
            if self.game.ended:
                return True
        agent = self._agent_for_current()
        if agent is None:
            return False
        pos = agent.select_move(self.game)
        if pos is None:
            # 无合法步（理论上 _reversi_auto_skip_or_end 已处理）
            return False
        try:
            self.game.step(Move(player=self.game.current, pos=pos))
            self.message = f"AI Move: {pos.row},{pos.col}"
            if normalize_game_type(self.game_type) == "reversi":
                self._reversi_check_full_end()
                if not self.game.ended:
                    self._reversi_auto_skip_or_end()
            return True
        except GameError:
            # 极少数竞态/非法（不应发生），忽略
            return False

    def _maybe_ai_play_loop(self):
        # 连续让所有AI方执行，直到轮到玩家或对局结束
        safety = 512
        progressed = True
        while progressed and safety > 0:
            progressed = self._maybe_ai_play_once()
            safety -= 1

    # ------- 事件接口 -------
    def click_canvas(self, evt) -> Tuple[object, Optional[str]]:
        if not self.game:
            return self.get_image(), "请先开始新对局"

        if normalize_game_type(self.game_type) == "reversi":
            self._reversi_auto_skip_or_end()
            if self.game.ended:
                return self.get_image(), self._ended_popup()

        if self.game.ended:
            return self.get_image(), "对局已结束，请开启新对局。"

        # 若轮到 AI，不允许玩家落子，直接触发 AI 回合
        agent = self._agent_for_current()
        if agent is not None:
            self._maybe_ai_play_loop()
            img = self.get_image()
            if self.game.ended:
                return img, self._ended_popup()
            return img, None

        pos = self.renderer.coord_from_xy(evt.index[0], evt.index[1], self.game.board)
        if pos is None:
            self.message = "Please click near a grid intersection"
            return self.get_image(), "请点击靠近网格交点的位置"

        move = Move(player=self.game.current, pos=pos)
        try:
            self.game.step(move)
            self.message = f"Move: {pos.row},{pos.col}"
            if normalize_game_type(self.game_type) == "reversi":
                self._reversi_check_full_end()
                if not self.game.ended:
                    self._reversi_auto_skip_or_end()
            # 玩家走子后，若轮到AI，自动走
            self._maybe_ai_play_loop()
            img = self.get_image()
            if self.game.ended:
                return img, self._ended_popup()
            return img, None
        except GameError as e:
            self.message = "Illegal move or operation"
            if normalize_game_type(self.game_type) == "reversi":
                return self.get_image(), "非法落子：该位置无法翻转对方棋子"
            return self.get_image(), f"错误：{str(e)}"

    def do_pass(self) -> Tuple[object, Optional[str]]:
        # 仅围棋允许“虚着”
        if not self.game:
            return self.get_image(), "请先开始新对局"
        from core.go import GoGame
        if not isinstance(self.game, GoGame):
            return self.get_image(), "仅围棋可使用虚着"
        if self.game.ended:
            return self.get_image(), "对局已结束，请开启新对局。"
        try:
            self.game.step(Move(player=self.game.current, pass_move=True))
            if self.game.ended:
                self.message = "Both passed. Scoring."
                # 围棋终局后不再触发AI（围棋未启用AI）
                return self.get_image(), self._ended_popup()
            else:
                self.message = "Pass"
                return self.get_image(), "虚着成功"
        except GameError as e:
            self.message = "Illegal move or operation"
            return self.get_image(), f"错误：{str(e)}"

    def resign(self) -> Tuple[object, Optional[str]]:
        if not self.game:
            return self.get_image(), "请先开始新对局"
        if self.game.ended:
            return self.get_image(), "对局已结束，请开启新对局。"
        try:
            self.game.step(Move(player=self.game.current, resign=True))
            self.message = "Resign"
            return self.get_image(), self._ended_popup()
        except GameError as e:
            self.message = "Illegal move or operation"
            return self.get_image(), f"错误：{str(e)}"

    def undo(self) -> Tuple[object, Optional[str]]:
        if not self.game:
            return self.get_image(), "请先开始新对局"
        ok = self.game.undo()
        self.message = "Undo" if ok else "No move to undo"
        return self.get_image(), ("悔棋成功" if ok else "无棋可悔")

    def save(self, text_path: str):
        if not self.game:
            return self.get_image(), "请先开始新对局"
        if not text_path:
            return self.get_image(), "请输入保存文件名（如 save.json）"
        try:
            canon = normalize_game_type(self.game_type)
        except Exception:
            canon = "go"
        data = self.game.serialize()
        with open(text_path, "w", encoding="utf-8") as f:
            json.dump({
                "meta": {"type": canon, "size": self.size, "komi": getattr(self.game, "komi", None)},
                "data": data
            }, f, ensure_ascii=False, indent=2)
        self.message = f"Saved to {text_path}"
        return self.get_image(), f"已保存到 {text_path}"

    def load(self, text_path: str):
        if not text_path:
            return self.get_image(), "请输入要读取的文件名"
        try:
            with open(text_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            meta = obj.get("meta", {})
            data = obj.get("data")
            if not data:
                raise ValueError("存档损坏")

            meta_type = meta.get("type")
            gt = None
            if meta_type:
                gt = normalize_game_type(meta_type)
            else:
                raw = data.get("type")
                if raw:
                    try:
                        gt = normalize_game_type(raw)
                    except Exception:
                        gt = None
            if gt is None:
                gt = "gomoku"

            self.game_type = ("围棋" if gt == "go" else ("五子棋" if gt == "gomoku" else "黑白棋"))
            self.size = meta.get("size", len(data["board"]))
            self.komi = meta.get("komi", 7.5) or 7.5

            self.game = create_game(gt, self.size, self.komi)
            self.game.deserialize(data)
            self.message = f"Loaded: {self.game_type} {self.size}"

            # 读档后根据当前UI配置重建AI（不从存档恢复AI配置）
            self._refresh_ai_agents()
            # 如果轮到AI则自动走
            self._maybe_ai_play_loop()

            return self.get_image(), f"读取存档成功：{self.game_type} {self.size}"
        except Exception as e:
            self.message = "Load failed"
            return self.get_image(), f"读取失败：{e}"