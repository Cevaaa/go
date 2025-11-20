from __future__ import annotations
from typing import Optional
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
        self.message = "欢迎使用棋类对战平台"
        self.theme = "wood"

    def new_game(self, game_type: str, size: int, komi: float):
        if size < 8 or size > 19:
            raise GameError("棋盘大小需在 8~19 之间")
        self.game_type = game_type
        self.size = size
        self.komi = komi
        self.game = create_game(game_type, size, komi)
        self.message = f"新对局开始：{game_type} {size}x{size}"
        return self.get_image()

    def _turn_label(self):
        if not self.game:
            return ""
        if self.game.ended:
            if self.game_type.lower() in ("go","weiqi","围棋"):
                # if ended due to pass-pass, display pending score
                from core.go import GoGame
                if isinstance(self.game, GoGame):
                    score = self.game.score()
                    if score is not None:
                        b = score["BLACK"]
                        w = score["WHITE"]
                        if b > w:
                            return f"终局：黑胜（黑 {b:.1f} : 白 {w:.1f}，白贴目 {self.game.komi}）"
                        elif w > b:
                            return f"终局：白胜（黑 {b:.1f} : 白 {w:.1f}，白贴目 {self.game.komi}）"
                        else:
                            return f"终局：平局（黑 {b:.1f} : 白 {w:.1f}）"
            # gomoku ended
            if self.game.winner is None:
                return "终局：平局"
            else:
                return f"终局：{'黑' if self.game.winner==PlayerColor.BLACK else '白'}胜"
        else:
            return f"轮到：{'黑' if self.game.current==PlayerColor.BLACK else '白'}"

    def get_image(self):
        if not self.game:
            return None
        text = f"{self.message} | {self._turn_label()}"
        return self.renderer.render(
            self.game.board, self.game_type, self.game.last_pos, text,
            None if self.game.ended else self.game.current, self.theme
        )

    def click_canvas(self, evt):
        if not self.game:
            self.message = "请先开始新对局"
            return self.get_image()
        if self.game.ended:
            self.message = "对局已结束，请重新开始"
            return self.get_image()
        pos = self.renderer.coord_from_xy(evt.index[0], evt.index[1], self.game.board)
        if pos is None:
            self.message = "请点击靠近网格交点的位置"
            return self.get_image()
        move = Move(player=self.game.current, pos=pos)
        try:
            self.game.step(move)
            self.message = f"落子：{pos.row},{pos.col}"
        except GameError as e:
            self.message = f"错误：{str(e)}"
        return self.get_image()

    def do_pass(self):
        if not self.game:
            self.message = "请先开始新对局"
            return self.get_image()
        from core.go import GoGame
        if not isinstance(self.game, GoGame):
            self.message = "仅围棋可虚着"
            return self.get_image()
        if self.game.ended:
            self.message = "对局已结束"
            return self.get_image()
        try:
            self.game.step(Move(player=self.game.current, pass_move=True))
            if self.game.ended:
                self.message = "双方连续虚着，进入结算"
            else:
                self.message = "虚着成功"
        except GameError as e:
            self.message = f"错误：{str(e)}"
        return self.get_image()

    def resign(self):
        if not self.game:
            self.message = "请先开始新对局"
            return self.get_image()
        if self.game.ended:
            self.message = "对局已结束"
            return self.get_image()
        try:
            self.game.step(Move(player=self.game.current, resign=True))
            self.message = "认负：对局结束"
        except GameError as e:
            self.message = f"错误：{str(e)}"
        return self.get_image()

    def undo(self):
        if not self.game:
            self.message = "请先开始新对局"
            return self.get_image()
        ok = self.game.undo()
        self.message = "悔棋成功" if ok else "无棋可悔"
        return self.get_image()

    def save(self, text_path: str):
        if not self.game:
            self.message = "请先开始新对局"
            return self.get_image()
        if not text_path:
            self.message = "请输入保存文件名（如 save.json）"
            return self.get_image()
        data = self.game.serialize()
        with open(text_path, "w", encoding="utf-8") as f:
            json.dump({
                "meta": {"type": self.game_type, "size": self.size, "komi": getattr(self.game, "komi", None)},
                "data": data
            }, f, ensure_ascii=False, indent=2)
        self.message = f"已保存到 {text_path}"
        return self.get_image()

    def load(self, text_path: str):
        if not text_path:
            self.message = "请输入要读取的文件名"
            return self.get_image()
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
            self.message = f"读取存档成功：{self.game_type} {self.size}"
        except Exception as e:
            self.message = f"读取失败：{e}"
        return self.get_image()