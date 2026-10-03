"""Screenshot -> Zip grid using classical image processing (no ML).

The board is found from its evenly spaced gray grid lines; numbered cells are
black disks; digits are white blobs inside a disk, matched against templates.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

TEMPLATE_PATH = Path(__file__).with_name("digits.npz")
GLYPH = 24  # side of the normalized digit image


@dataclass
class Board:
    grid: list[list[int]]
    xs: list[float]  # N+1 vertical line positions
    ys: list[float]  # N+1 horizontal line positions

    def center(self, r, c):
        return ((self.xs[c] + self.xs[c + 1]) / 2, (self.ys[r] + self.ys[r + 1]) / 2)


class ParseError(Exception):
    pass


def _line_centers(profile, thresh):
    """Group above-threshold indices of a 1-D profile into line centers."""
    idx = np.flatnonzero(profile >= thresh)
    if idx.size == 0:
        return []
    groups = np.split(idx, np.flatnonzero(np.diff(idx) > 2) + 1)
    return [float(g.mean()) for g in groups]


def _longest_even_chain(pos, spacing, tol):
    """Longest run of positions spaced `spacing` apart (within tol)."""
    best = []
    for i, start in enumerate(pos):
        chain = [start]
        for p in pos[i + 1:]:
            gap = p - chain[-1]
            if abs(gap - spacing) <= tol:
                chain.append(p)
            elif gap > spacing + tol:
                break
        if len(chain) > len(best):
            best = chain
    return best


def find_grid(gray):
    """Locate grid line positions. Returns (xs, ys)."""
    lines = (gray > 100) & (gray < 225)
    h, w = gray.shape

    col = lines.sum(axis=0)
    xs = _line_centers(col, 0.6 * col.max())
    if len(xs) < 3:
        raise ParseError("could not find vertical grid lines")
    spacing = float(np.median(np.diff(xs)))
    xs = _longest_even_chain(xs, spacing, 0.15 * spacing)

    x0, x1 = int(xs[0]), int(xs[-1])
    row = lines[:, x0:x1].sum(axis=1)
    ys = _line_centers(row, 0.6 * (x1 - x0))
    ys = _longest_even_chain(ys, spacing, 0.15 * spacing)

    n = len(xs) - 1
    if n < 2 or len(ys) != n + 1:
        raise ParseError(f"inconsistent grid: {len(xs)} vertical vs {len(ys)} horizontal lines")
    return xs, ys


def _normalize(glyph_mask):
    """Crop a binary glyph to its box, pad to square keeping aspect, resize."""
    ys, xs = np.nonzero(glyph_mask)
    g = glyph_mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8) * 255
    h, w = g.shape
    side = max(h, w)
    sq = np.zeros((side, side), np.uint8)
    sq[(side - h) // 2:(side - h) // 2 + h, (side - w) // 2:(side - w) // 2 + w] = g
    return cv2.resize(sq, (GLYPH, GLYPH), interpolation=cv2.INTER_AREA).astype(np.float32) / 255


def cell_glyphs(cell):
    """Return normalized digit glyphs (left to right) if the cell holds a disk, else None."""
    dark = cell < 110
    if dark.mean() < 0.2:
        return None
    count, labels, stats, _ = cv2.connectedComponentsWithStats(dark.astype(np.uint8), connectivity=8)
    disk_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    contours, _ = cv2.findContours((labels == disk_label).astype(np.uint8),
                                   cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    disk = np.zeros(cell.shape, np.uint8)
    cv2.drawContours(disk, contours, -1, 1, thickness=cv2.FILLED)
    disk = cv2.erode(disk, np.ones((5, 5), np.uint8))

    white = (disk > 0) & (cell > 150)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(white.astype(np.uint8), connectivity=8)
    min_area = 0.004 * cell.size
    blobs = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= min_area]
    blobs.sort(key=lambda i: stats[i, cv2.CC_STAT_LEFT])
    if not blobs:
        raise ParseError("found a disk with no digits")
    return [_normalize(labels == i) for i in blobs]


def iter_cells(gray, xs, ys):
    """Yield (r, c, cell_image) with a margin trimmed to drop the grid lines."""
    n = len(xs) - 1
    for r in range(n):
        for c in range(n):
            mx = int(0.08 * (xs[c + 1] - xs[c]))
            my = int(0.08 * (ys[r + 1] - ys[r]))
            yield r, c, gray[int(ys[r]) + my:int(ys[r + 1]) - my, int(xs[c]) + mx:int(xs[c + 1]) - mx]


def load_templates(path=TEMPLATE_PATH):
    data = np.load(path)
    return {int(k): data[k] for k in data.files}


def classify(glyph, templates):
    return min(templates, key=lambda d: float(np.abs(templates[d] - glyph).sum()))


def parse(image, templates=None):
    """Parse a BGR screenshot into a Board."""
    templates = templates or load_templates()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    xs, ys = find_grid(gray)
    n = len(xs) - 1
    grid = [[0] * n for _ in range(n)]
    for r, c, cell in iter_cells(gray, xs, ys):
        glyphs = cell_glyphs(cell)
        if glyphs:
            grid[r][c] = int("".join(str(classify(g, templates)) for g in glyphs))

    nums = sorted(v for row in grid for v in row if v)
    if nums != list(range(1, len(nums) + 1)):
        shown = "\n".join(" ".join(f"{v:2d}" for v in row) for row in grid)
        raise ParseError(f"digits misread (expected 1..{len(nums)}, got {nums}):\n{shown}")
    return Board(grid, xs, ys)
