from __future__ import annotations
from typing import Optional, Tuple
import json
from core.models import PlayerColor, Move, Position, GameError
from core.factory import create_game
from .renderer import ImageRenderer

class UIController:
    def __init__(self):
        self.game = None
        self.renderer = ImageRenderer()
        self.game_type = "围棋"
        self.size = 19
        self.komi = 7.5
        self.message = "Welcome to the Board Game Platform"  # 渲染文字改英文
        self.theme = "wood"

    def set_theme(self, theme: str):
        # 确保主题立即生效
        self.theme = theme
        self.renderer.set_theme(theme)

    def new_game(self, game_type: str, size: int, komi: float):
        if size < 8 or size > 19:
            raise GameError("棋盘大小需在 8~19 之间")
        self.game_type = game_type
        self.size = size
        self.komi = komi
        self.game = create_game(game_type, size, komi)
        # 这里的 message 为英文（仅用于 Pillow 渲染）
        self.message = f"New game: {game_type} {size}x{size}"
        return self.get_image()

    def _turn_label(self):
        # 返回英文标签用于图片渲染
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
            None if self.game.ended else self.game.current
        )

    def _ended_popup(self) -> Optional[str]:
        # 中文弹窗提示
        if not self.game or not self.game.ended:
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
        # 五子棋或认负结束
        if self.game.winner is None:
            return "平局！请开启新对局。"
        else:
            return f"{'黑方' if self.game.winner==PlayerColor.BLACK else '白方'}胜利！请开启新对局。"

    def click_canvas(self, evt) -> Tuple[object, Optional[str]]:
        if not self.game:
            # UI 中文提示
            popup = "请先开始新对局"
            return self.get_image(), popup
        if self.game.ended:
            # 对局结束后再次点击的提示
            popup = "对局已结束，请开启新对局。"
            return self.get_image(), popup
        pos = self.renderer.coord_from_xy(evt.index[0], evt.index[1], self.game.board)
        if pos is None:
            # 仅图片文字英文，弹窗中文
            self.message = "Please click near a grid intersection"
            return self.get_image(), "请点击靠近网格交点的位置"
        move = Move(player=self.game.current, pos=pos)
        try:
            self.game.step(move)
            self.message = f"Move: {pos.row},{pos.col}"
            img = self.get_image()
            # 如果此手导致胜负，给出弹窗
            if self.game.ended:
                return img, self._ended_popup()
            return img, None
        except GameError as e:
            # 渲染消息改为英文，弹窗中文
            self.message = "Illegal move or operation"
            return self.get_image(), f"错误：{str(e)}"

    def do_pass(self) -> Tuple[object, Optional[str]]:
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
        data = self.game.serialize()
        with open(text_path, "w", encoding="utf-8") as f:
            json.dump({
                "meta": {"type": self.game_type, "size": self.size, "komi": getattr(self.game, "komi", None)},
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
            self.game_type = meta.get("type", data.get("type", "围棋"))
            self.size = meta.get("size", len(data["board"]))
            self.komi = meta.get("komi", 7.5) or 7.5
            self.game = create_game(self.game_type, self.size, self.komi)
            self.game.deserialize(data)
            self.message = f"Loaded: {self.game_type} {self.size}"
            return self.get_image(), f"读取存档成功：{self.game_type} {self.size}"
        except Exception as e:
            self.message = "Load failed"
            return self.get_image(), f"读取失败：{e}"