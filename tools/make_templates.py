"""Build zipsolve/digits.npz from a screenshot whose grid is known.

Usage: python tools/make_templates.py tests/fixtures/hard_8x8.png tests/fixtures/hard_8x8.txt
"""

import sys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zipsolve.parse import TEMPLATE_PATH, cell_glyphs, find_grid, iter_cells  # noqa: E402


def main(image_path, grid_path):
    gray = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2GRAY)
    truth = [list(map(int, line.split())) for line in open(grid_path) if line.strip()]
    xs, ys = find_grid(gray)
    samples = defaultdict(list)
    for r, c, cell in iter_cells(gray, xs, ys):
        glyphs = cell_glyphs(cell)
        if not truth[r][c]:
            assert glyphs is None, f"unexpected disk at {r},{c}"
            continue
        digits = str(truth[r][c])
        assert glyphs and len(glyphs) == len(digits), f"glyph count mismatch at {r},{c}"
        for d, g in zip(digits, glyphs):
            samples[d].append(g)
    missing = set("0123456789") - set(samples)
    if missing:
        sys.exit(f"no samples for digits {sorted(missing)}")
    np.savez_compressed(TEMPLATE_PATH, **{d: np.mean(gs, axis=0) for d, gs in samples.items()})
    print(f"wrote {TEMPLATE_PATH} ({ {d: len(g) for d, g in sorted(samples.items())} })")


if __name__ == "__main__":
    main(*sys.argv[1:3])
