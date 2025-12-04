from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Callable
import time
from core.models import PlayerColor, Move, Position

@dataclass
class ReplayEvent:
    type: str               # "move" | "pass" | "resign" | "skip"
    player: Optional[str]   # "BLACK" | "WHITE" | None
    row: Optional[int] = None
    col: Optional[int] = None
    ts: float = 0.0
    snap_index: int = 0     # index into snapshots array (nearest keyframe)

class Recorder:
    def __init__(self, keyframe_every: int = 10):
        self.enabled: bool = True
        self.events: List[ReplayEvent] = []
        self.snapshots: List[Dict[str, Any]] = []   # Game.snapshot()
        self.k: int = max(1, int(keyframe_every))
        self._start_ts: Optional[float] = None
        # 新增：可选的元数据（双方用户名等）
        self.meta: Dict[str, Any] = {"users": {"black": None, "white": None}}

    def set_users(self, black_user: Optional[str], white_user: Optional[str]):
        self.meta["users"] = {"black": black_user, "white": white_user}

    def start(self):
        self.events.clear()
        self.snapshots.clear()
        self._start_ts = time.time()

    def stop(self):
        self._start_ts = None

    def _now(self) -> float:
        if self._start_ts is None:
            return 0.0
        return time.time() - self._start_ts

    def _maybe_keyframe(self, game) -> int:
        if not self.snapshots:
            self.snapshots.append(game.snapshot())
            return 0
        if (len(self.events) % self.k) == 0:
            self.snapshots.append(game.snapshot())
        return len(self.snapshots) - 1

    def on_move(self, game, move: Move):
        if not self.enabled:
            return
        idx = self._maybe_keyframe(game)
        p = move.pos
        self.events.append(ReplayEvent(
            type="move",
            player="BLACK" if move.player == PlayerColor.BLACK else "WHITE",
            row=p.row if p else None,
            col=p.col if p else None,
            ts=self._now(),
            snap_index=idx
        ))

    def on_pass(self, game, player: PlayerColor):
        if not self.enabled:
            return
        idx = self._maybe_keyframe(game)
        self.events.append(ReplayEvent(
            type="pass",
            player="BLACK" if player == PlayerColor.BLACK else "WHITE",
            ts=self._now(),
            snap_index=idx
        ))

    def on_resign(self, game, player: PlayerColor):
        if not self.enabled:
            return
        idx = self._maybe_keyframe(game)
        self.events.append(ReplayEvent(
            type="resign",
            player="BLACK" if player == PlayerColor.BLACK else "WHITE",
            ts=self._now(),
            snap_index=idx
        ))

    def on_skip(self, game, player: PlayerColor):
        if not self.enabled:
            return
        idx = self._maybe_keyframe(game)
        self.events.append(ReplayEvent(
            type="skip",
            player="BLACK" if player == PlayerColor.BLACK else "WHITE",
            ts=self._now(),
            snap_index=idx
        ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "k": self.k,
            "events": [asdict(e) for e in self.events],
            "snapshots": self.snapshots,
            "meta": self.meta,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Recorder":
        r = Recorder(keyframe_every=d.get("k", 10))
        r.enabled = d.get("enabled", True)
        r.events = [ReplayEvent(**e) for e in d.get("events", [])]
        r.snapshots = d.get("snapshots", [])
        r.meta = d.get("meta", {"users": {"black": None, "white": None}})
        return r

class Replayer:
    def __init__(self):
        self.events: List[ReplayEvent] = []
        self.snapshots: List[Dict[str, Any]] = []
        self.k: int = 10
        self.index: int = -1
        self._factory: Optional[Callable[[str, int, float], Any]] = None
        self._init_meta: Dict[str, Any] = {}
        self._game: Optional[Any] = None

    def bind_factory(self, f: Callable[[str, int, float], Any]):
        self._factory = f

    def load(self, init_meta: Dict[str, Any], snapshots: List[Dict[str, Any]], events: List[ReplayEvent], k: int):
        self._init_meta = init_meta
        self.snapshots = snapshots or []
        self.events = events or []
        self.k = max(1, int(k or 10))
        self.index = -1
        if self._factory:
            gt = init_meta.get("type", "gomoku")
            size = int(init_meta.get("size", 19))
            komi = float(init_meta.get("komi", 7.5) or 7.5)
            self._game = self._factory(gt, size, komi)
            if self.snapshots:
                self._game.restore(self.snapshots[0])
            if hasattr(self._game, "recorder") and self._game.recorder:
                self._game.recorder.enabled = False

    @property
    def game(self):
        return self._game

    def total(self) -> int:
        return len(self.events)

    def current_index(self) -> int:
        return self.index

    def reset_to_start(self):
        self.index = -1
        if self._game and self.snapshots:
            self._game.restore(self.snapshots[0])

    def _apply_event_no_step(self, e: ReplayEvent):
        if not self._game:
            return
        rec_prev = None
        if hasattr(self._game, "recorder"):
            rec_prev = self._game.recorder.enabled
            self._game.recorder.enabled = False
        try:
            if e.type == "skip":
                self._game.current = PlayerColor.WHITE if self._game.current == PlayerColor.BLACK else PlayerColor.BLACK
                return
            if e.player:
                want = PlayerColor.BLACK if e.player == "BLACK" else PlayerColor.WHITE
                self._game.current = want
            if e.type == "move":
                pos = Position(e.row, e.col) if e.row is not None and e.col is not None else None
                mv = Move(player=self._game.current, pos=pos)
            elif e.type == "pass":
                mv = Move(player=self._game.current, pass_move=True)
            elif e.type == "resign":
                mv = Move(player=self._game.current, resign=True)
            else:
                return
            if not self._game.is_legal(mv):
                return
            self._game.apply_move(mv)
        finally:
            if hasattr(self._game, "recorder") and rec_prev is not None:
                self._game.recorder.enabled = rec_prev

    def seek(self, n: int):
        n = max(-1, min(n, self.total()-1))
        if not self._game:
            self.index = n
            return
        if n == self.index:
            return
        if self.snapshots:
            key_idx = max(0, min(n // self.k, len(self.snapshots)-1)) if n >= 0 else 0
            self._game.restore(self.snapshots[key_idx])
            if hasattr(self._game, "recorder"):
                self._game.recorder.enabled = False
            start_event = key_idx * self.k
        else:
            if hasattr(self._game, "recorder"):
                self._game.recorder.enabled = False
            start_event = 0
        if n >= 0:
            for i in range(start_event, n+1):
                e = self.events[i]
                self._apply_event_no_step(e)
        self.index = n

    def step_next(self) -> bool:
        if self.index >= self.total()-1:
            return False
        self.seek(self.index + 1)
        return True

    def step_prev(self) -> bool:
        if self.index <= -1:
            return False
        self.seek(self.index - 1)
        return True