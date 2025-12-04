from __future__ import annotations
from typing import Optional, Tuple
import json
import threading
import time

from core.models import PlayerColor, Move, Position, GameError
from core.factory import create_game, normalize_game_type
from .renderer import ImageRenderer

# AI（保持第二阶段AI版本）
from core.ai.base import IGameAI
from core.ai.random_ai import RandomReversiAI
from core.ai.reversi_rule_ai import HeuristicReversiAI

# 回放
from core.replay import Replayer, Recorder, ReplayEvent

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
        self.ai_level = 1
        self._ai_black: Optional[IGameAI] = None
        self._ai_white: Optional[IGameAI] = None
        # 回放控制
        self.replay_mode: bool = False
        self.replayer: Optional[Replayer] = None
        self.replay_speed: float = 1.0   # 1x
        self._play_thread: Optional[threading.Thread] = None
        self._play_flag: bool = False

    def set_theme(self, theme: str):
        self.theme = theme
        self.renderer.set_theme(theme)

    def _build_ai(self, level: int) -> IGameAI:
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
        self._stop_play_thread()
        self.replay_mode = False
        self.replayer = None

        self.game_type = game_type
        self.size = size
        self.komi = komi
        self.black_side = black_side
        self.white_side = white_side
        self.ai_kind = ai_kind
        self.ai_level = int(ai_level)
        self.game = create_game(game_type, size, komi)

        # 新对局录像默认开启
        if hasattr(self.game, "recorder"):
            self.game.recorder.enabled = True
            self.game.recorder.start()

        self._refresh_ai_agents()
        if normalize_game_type(game_type) != "reversi" and (self.black_side == "AI" or self.white_side == "AI"):
            self.black_side = "玩家"
            self.white_side = "玩家"
            self._ai_black = None
            self._ai_white = None
            self.message = "AI is only available for Reversi currently. Switched to PvP."
        else:
            self.message = f"New game: {game_type} {size}x{size}"
        self._maybe_ai_play_loop()
        return self.get_image()

    def _turn_label(self):
        if not self.game:
            return ""
        if self.replay_mode:
            idx = self.replayer.current_index() if self.replayer else -1
            total = self.replayer.total() if self.replayer else 0
            return f"Replay: {idx+1}/{total}"
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
        prev = self.game.current
        self.game.current = PlayerColor.WHITE if self.game.current == PlayerColor.BLACK else PlayerColor.BLACK
        self.message = "No legal move; turn skipped."
        # 录像：记录 skip
        self.game.record_skip(prev)
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
        if self.replay_mode:
            return None
        if normalize_game_type(self.game_type) != "reversi":
            return None
        if self.game.current == PlayerColor.BLACK:
            return self._ai_black
        else:
            return self._ai_white

    def _maybe_ai_play_once(self) -> bool:
        if not self.game or self.game.ended or self.replay_mode:
            return False
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
            return False

    def _maybe_ai_play_loop(self):
        safety = 512
        progressed = True
        while progressed and safety > 0:
            progressed = self._maybe_ai_play_once()
            safety -= 1

    # ------- 事件接口（交互/保存/读取） -------
    def click_canvas(self, evt) -> Tuple[object, Optional[str]]:
        if not self.game:
            return self.get_image(), "请先开始新对局"

        if self.replay_mode:
            return self.get_image(), "回放模式中，无法下子。"

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
        if not self.game:
            return self.get_image(), "请先开始新对局"
        if self.replay_mode:
            return self.get_image(), "回放模式中，无法操作。"
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
        if self.replay_mode:
            return self.get_image(), "回放模式中，无法操作。"
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
        if self.replay_mode:
            return self.get_image(), "回放模式中，无法操作。"
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
            self._stop_play_thread()
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

            # 如有录像数据，准备回放器
            rep = data.get("replay")
            if rep and rep.get("events"):
                self._prepare_replayer_from_data(gt, rep)
            else:
                self.replay_mode = False
                self.replayer = None

            # 读档后，若未进入回放，且轮到AI则自动走
            if not self.replay_mode:
                self._refresh_ai_agents()
                self._maybe_ai_play_loop()

            return self.get_image(), f"读取存档成功：{self.game_type} {self.size}"
        except Exception as e:
            self.message = "Load failed"
            return self.get_image(), f"读取失败：{e}"

    # ------- 回放控制 -------
    def _prepare_replayer_from_data(self, canon_type: str, rep_dict):
        events = [ReplayEvent(**e) for e in rep_dict.get("events", [])]
        snapshots = rep_dict.get("snapshots", [])
        k = rep_dict.get("k", 10)
        meta = {"type": canon_type, "size": self.size, "komi": self.komi}
        self.replayer = Replayer()
        self.replayer.bind_factory(lambda t, s, kmi: create_game(t, s, kmi))
        self.replayer.load(meta, snapshots, events, k)
        # 将回放游戏状态替换到 UI 的 game 上（共享渲染）
        if self.replayer.game:
            self.game = self.replayer.game
        self.replay_mode = True
        self.message = "Replay loaded. Use controls to play."

    def replay_enter_from_current(self):
        # 从当前对局（含 recorder）进入回放（常用于新局或旧存档无 replay）
        if not self.game or not hasattr(self.game, "recorder"):
            return self.get_image(), "当前对局无法进入回放。"
        rep = self.game.recorder.to_dict()
        if not rep.get("events"):
            return self.get_image(), "当前没有可回放的事件。"
        canon = normalize_game_type(self.game_type)
        self._prepare_replayer_from_data(canon, rep)
        return self.get_image(), "已进入回放模式。"

    def replay_toggle_record(self, on: bool):
        if not self.game or not hasattr(self.game, "recorder"):
            return self.get_image(), "当前对局不支持录像。"
        self.game.recorder.enabled = bool(on)
        if on:
            self.game.recorder.start()
            return self.get_image(), "录像已开启。"
        else:
            self.game.recorder.stop()
            return self.get_image(), "录像已关闭。"

    def replay_set_speed(self, speed: float):
        self.replay_speed = max(0.25, min(4.0, float(speed)))
        return self.get_image(), f"回放速度：{self.replay_speed}x"

    def replay_start(self):
        if not self.replay_mode or not self.replayer:
            return self.get_image(), "未处于回放模式。"
        if self._play_thread and self._play_thread.is_alive():
            self._play_flag = True
            return self.get_image(), None
        self._play_flag = True
        self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self._play_thread.start()
        return self.get_image(), None

    def _play_loop(self):
        while self._play_flag and self.replayer and self.replayer.step_next():
            # 推进一帧后，要求UI刷新；此处仅更新 message，UI 层通过回调刷新图像
            self.message = "Replaying..."
            time.sleep(max(0.05, 0.6 / self.replay_speed))
        self._play_flag = False
        self.message = "Replay paused or ended."

    def replay_pause(self):
        self._play_flag = False
        return self.get_image(), None

    def replay_stop(self):
        self._stop_play_thread()
        if self.replay_mode and self.replayer:
            self.replayer.reset_to_start()
        return self.get_image(), "回放已停止。"

    def _stop_play_thread(self):
        self._play_flag = False
        if self._play_thread and self._play_thread.is_alive():
            try:
                self._play_thread.join(timeout=0.1)
            except:
                pass
        self._play_thread = None

    def replay_next(self):
        if not self.replay_mode or not self.replayer:
            return self.get_image(), "未处于回放模式。"
        ok = self.replayer.step_next()
        if not ok:
            return self.get_image(), "已到最后一步。"
        return self.get_image(), None

    def replay_prev(self):
        if not self.replay_mode or not self.replayer:
            return self.get_image(), "未处于回放模式。"
        ok = self.replayer.step_prev()
        if not ok:
            return self.get_image(), "已在起始位置。"
        return self.get_image(), None