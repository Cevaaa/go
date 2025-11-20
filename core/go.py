from __future__ import annotations
from typing import Optional, Dict, Any
from .game import Game
from .models import PlayerColor, Piece, Position, Move, GameError
from .rules import flood_group_and_liberties, capture_if_no_liberty

class GoGame(Game):
    def __init__(self, size: int, komi: float = 7.5):
        super().__init__(size)
        self.captured_black = 0  # black stones captured by White
        self.captured_white = 0  # white stones captured by Black
        self.consecutive_pass = 0
        self.komi = komi

    def reset(self, size: int, komi: Optional[float] = None):
        super().reset(size)
        self.captured_black = 0
        self.captured_white = 0
        self.consecutive_pass = 0
        if komi is not None:
            self.komi = komi

    def snapshot(self):
        base = super().snapshot()
        base.update({
            "captured_black": self.captured_black,
            "captured_white": self.captured_white,
            "consecutive_pass": self.consecutive_pass,
            "komi": self.komi,
        })
        return base

    def restore(self, snap):
        super().restore(snap)
        self.captured_black = snap.get("captured_black", 0)
        self.captured_white = snap.get("captured_white", 0)
        self.consecutive_pass = snap.get("consecutive_pass", 0)
        self.komi = snap.get("komi", 7.5)

    def is_legal(self, move: Move) -> bool:
        if move.resign:
            return True
        if move.pass_move:
            return True
        if move.pos is None:
            return False
        p = move.pos
        if not self.board.in_bounds(p):
            return False
        if not self.board.is_empty(p):
            return False
        # simulate
        piece = Piece.from_player(move.player)
        self.board.set(p, piece)
        # capture opponent neighbors without liberties
        opp_piece = Piece.BLACK if piece == Piece.WHITE else Piece.WHITE
        adj_opp = [nb for nb in self.board.neighbors(p) if self.board.get(nb) == opp_piece]
        captured = 0
        # copy then operate on temp board: we directly use board then revert (simple and safe here)
        # capture (on temp: but we used real board, so we need to remember and revert)
        to_clear = []
        for nb in adj_opp:
            stones, libs = flood_group_and_liberties(self.board, nb)
            if len(libs) == 0:
                to_clear.extend(list(stones))
        for s in to_clear:
            self.board.set(s, Piece.EMPTY)
            captured += 1
        # now check self liberties
        stones, libs = flood_group_and_liberties(self.board, p)
        legal = len(libs) > 0 or captured > 0  # suicide forbidden unless capture occurs
        # revert simulation
        self.board.set(p, Piece.EMPTY)
        for s in to_clear:
            self.board.set(s, opp_piece)
        return legal

    def apply_move(self, move: Move):
        if move.resign:
            self.ended = True
            self._winner = PlayerColor.WHITE if move.player == PlayerColor.BLACK else PlayerColor.BLACK
            return
        if move.pass_move:
            self.consecutive_pass += 1
            self.last_pos = None
            if self.consecutive_pass >= 2:
                self.ended = True
                # winner determined at scoring time (UI会调用 get_state 信息并显示待结算提示)
            else:
                self.current = PlayerColor.WHITE if self.current == PlayerColor.BLACK else PlayerColor.BLACK
            return

        # place stone
        p = move.pos
        piece = Piece.from_player(move.player)
        self.board.set(p, piece)
        self.last_pos = p
        # reset pass chain
        self.consecutive_pass = 0

        # capture opponent
        opp_piece = Piece.BLACK if piece == Piece.WHITE else Piece.WHITE
        adj_opp = [nb for nb in self.board.neighbors(p) if self.board.get(nb) == opp_piece]
        before_counts = (self.captured_black, self.captured_white)
        captured = capture_if_no_liberty(self.board, adj_opp)
        if captured > 0:
            if opp_piece == Piece.BLACK:
                self.captured_black += captured
            else:
                self.captured_white += captured

        # if self group has no liberties after move (and no capture), it's suicide (should have been rejected in is_legal)
        stones, libs = flood_group_and_liberties(self.board, p)
        if len(libs) == 0:
            # rollback to safe state (shouldn't happen)
            self.board.set(p, Piece.EMPTY)
            # restore captured counters not needed since capture wasn't applied if suicide occurred here
            raise GameError("非法：自杀点")

        # switch
        self.current = PlayerColor.WHITE if self.current == PlayerColor.BLACK else PlayerColor.BLACK

    def serialize(self):
        data = super().serialize()
        data.update({
            "captured_black": self.captured_black,
            "captured_white": self.captured_white,
            "consecutive_pass": self.consecutive_pass,
            "komi": self.komi,
        })
        return data

    def deserialize(self, data):
        super().deserialize(data)
        self.captured_black = data.get("captured_black", 0)
        self.captured_white = data.get("captured_white", 0)
        self.consecutive_pass = data.get("consecutive_pass", 0)
        self.komi = data.get("komi", 7.5)

    def score(self) -> Optional[Dict[str, float]]:
        """Compute territory scoring only after two consecutive passes or if ended already."""
        if not self.ended:
            return None
        # simple territory scoring: count empty intersections that are adjacent only to one color
        size = self.board.size
        visited = [[False]*size for _ in range(size)]
        def flood_empty(sr, sc):
            from collections import deque
            q = deque()
            q.append((sr, sc))
            area = []
            owners = set()
            visited[sr][sc] = True
            while q:
                r, c = q.popleft()
                area.append((r,c))
                for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < size and 0 <= nc < size:
                        if not visited[nr][nc]:
                            piece = self.board.grid[nr][nc]
                            if piece == Piece.EMPTY:
                                visited[nr][nc] = True
                                q.append((nr,nc))
                            elif piece == Piece.BLACK:
                                owners.add(PlayerColor.BLACK)
                            elif piece == Piece.WHITE:
                                owners.add(PlayerColor.WHITE)
            return area, owners

        territory_black = 0
        territory_white = 0
        for r in range(size):
            for c in range(size):
                if self.board.grid[r][c] == Piece.EMPTY and not visited[r][c]:
                    area, owners = flood_empty(r, c)
                    if owners == {PlayerColor.BLACK}:
                        territory_black += len(area)
                    elif owners == {PlayerColor.WHITE}:
                        territory_white += len(area)
        # score = territory + captures (+ komi to White)
        black_score = territory_black + self.captured_white
        white_score = territory_white + self.captured_black + self.komi
        return {"BLACK": black_score, "WHITE": white_score}