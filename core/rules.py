from __future__ import annotations
from typing import Tuple, Set, List
from .models import Position, Piece

def is_five_in_a_row(board, p: Position, piece: Piece) -> bool:
    # Check 4 directions (8 orientations merged)
    dirs = [(1,0),(0,1),(1,1),(1,-1)]
    size = board.size
    for dr, dc in dirs:
        count = 1
        # backward
        r, c = p.row - dr, p.col - dc
        while 0 <= r < size and 0 <= c < size and board.grid[r][c] == piece:
            count += 1
            r -= dr
            c -= dc
        # forward
        r, c = p.row + dr, p.col + dc
        while 0 <= r < size and 0 <= c < size and board.grid[r][c] == piece:
            count += 1
            r += dr
            c += dc
        if count >= 5:
            return True
    return False

def flood_group_and_liberties(board, start: Position) -> Tuple[Set[Position], Set[Position]]:
    """Return (stones, liberties) for the group at start."""
    color = board.get(start)
    if color == Piece.EMPTY:
        return set(), set()
    visited: Set[Position] = set()
    stones: Set[Position] = set()
    liberties: Set[Position] = set()
    stack: List[Position] = [start]
    while stack:
        p = stack.pop()
        if p in visited:
            continue
        visited.add(p)
        stones.add(p)
        for nb in board.neighbors(p):
            nb_piece = board.get(nb)
            if nb_piece == Piece.EMPTY:
                liberties.add(nb)
            elif nb_piece == color and nb not in visited:
                stack.append(nb)
    return stones, liberties

def capture_if_no_liberty(board, positions: List[Position]) -> int:
    """Capture opponent groups among given positions that have no liberties. Returns captured count."""
    captured = 0
    seen: Set[Position] = set()
    for p in positions:
        if p in seen:
            continue
        piece = board.get(p)
        if piece == Piece.EMPTY:
            continue
        stones, libs = flood_group_and_liberties(board, p)
        seen |= stones
        if len(libs) == 0:
            for s in stones:
                board.set(s, Piece.EMPTY)
            captured += len(stones)
    return captured