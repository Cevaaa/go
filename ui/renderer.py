from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from core.models import PlayerColor, Piece, Position
from core.board import Board

def _load_font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()

class ImageRenderer:
    def __init__(self, cell=36, margin=24, theme="wood"):
        self.cell = cell
        self.margin = margin
        self.theme = theme

    def render(self, board: Board, game_type: str, last: Optional[Position], msg: str, turn: Optional[PlayerColor], theme: Optional[str]=None):
        if theme:
            self.theme = theme
        size = board.size
        cell = self.cell
        margin = self.margin
        W = H = margin*2 + cell*(size-1)
        # background
        if self.theme == "wood":
            bg_color = (236, 200, 120)
            line_color = (60, 40, 10)
        else:
            bg_color = (240, 240, 240)
            line_color = (40, 40, 40)
        img = Image.new("RGB", (W, H+80), bg_color)
        draw = ImageDraw.Draw(img)

        # grid
        for i in range(size):
            x0 = margin
            x1 = margin + cell*(size-1)
            y = margin + i*cell
            draw.line((x0, y, x1, y), fill=line_color, width=2)
            x = margin + i*cell
            y0 = margin
            y1 = margin + cell*(size-1)
            draw.line((x, y0, x, y1), fill=line_color, width=2)

        # star points for Go standard (9x9, 13x13, 19x19)
        if game_type.lower() in ("go", "weiqi", "围棋"):
            stars = []
            if size == 19:
                pts = [3, 9, 15]
                for r in pts:
                    for c in pts:
                        stars.append((r,c))
            elif size == 13:
                pts = [3, 6, 9]
                for r in pts:
                    for c in pts:
                        stars.append((r,c))
            elif size == 9:
                pts = [2, 4, 6]
                for r in pts:
                    for c in pts:
                        stars.append((r,c))
            for r, c in stars:
                cx = margin + c*cell
                cy = margin + r*cell
                draw.ellipse((cx-4, cy-4, cx+4, cy+4), fill=line_color)

        # stones
        for r in range(size):
            for c in range(size):
                p = Position(r, c)
                piece = board.get(p)
                if piece == Piece.EMPTY:
                    continue
                cx = margin + c*cell
                cy = margin + r*cell
                radius = int(cell*0.45)
                if piece == Piece.BLACK:
                    color = (20, 20, 20)
                else:
                    color = (240, 240, 240)
                draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=color, outline=(0,0,0))
        # last move marker
        if last is not None:
            cx = margin + last.col*cell
            cy = margin + last.row*cell
            draw.rectangle((cx-6, cy-6, cx+6, cy+6), outline=(200,30,30), width=3)

        # footer text
        font = _load_font(16)
        footer = msg or ""
        if turn:
            footer = f"{footer}  当前手: {'黑' if turn==PlayerColor.BLACK else '白'}"
        draw.rectangle((0, H, W, H+80), fill=(250,250,250))
        draw.text((10, H+10), footer, fill=(30,30,30), font=font)

        return img

    def coord_from_xy(self, x, y, board: Board):
        # x,y in pixel, map to nearest grid intersection
        cell = self.cell
        margin = self.margin
        size = board.size
        grid_x = round((x - margin) / cell)
        grid_y = round((y - margin) / cell)
        if 0 <= grid_x < size and 0 <= grid_y < size:
            # check closeness
            px = margin + grid_x*cell
            py = margin + grid_y*cell
            if abs(px - x) <= cell*0.45 and abs(py - y) <= cell*0.45:
                return Position(grid_y, grid_x)
        return None