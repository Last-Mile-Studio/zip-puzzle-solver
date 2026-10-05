import json
from pathlib import Path

import cv2
import pytest

from zip_solver import main
from zipsolve.parse import parse
from zipsolve.solve import is_valid, solve

FIX = Path(__file__).parent / "fixtures"


def needs(name):
    # Screenshots are kept out of the repo; these tests run only where one exists locally.
    return pytest.mark.skipif(not (FIX / f"{name}.png").exists(), reason=f"{name}.png not present")


def load(name):
    """Return (image, grid, walls) for a fixture. Truth is .json (with walls) or .txt (grid only)."""
    image = cv2.imread(str(FIX / f"{name}.png"))
    if (FIX / f"{name}.json").exists():
        truth = json.loads((FIX / f"{name}.json").read_text())
        return image, truth["grid"], truth["walls"]
    grid = [list(map(int, l.split())) for l in open(FIX / f"{name}.txt") if l.strip()]
    return image, grid, []


def norm_walls(walls):
    return sorted(tuple(sorted(tuple(cell) for cell in w)) for w in walls)


def scaled(image, scale):
    if scale == 1.0:
        return image
    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    return cv2.resize(image, None, fx=scale, fy=scale, interpolation=interp)


CASES = ([("hard_8x8", s) for s in (1.0, 0.6, 0.8, 1.5)] + [("walls_7x7", s) for s in (1.0, 1.5, 3.0)]
         + [("walls_6x6", s) for s in (1.0, 0.6, 0.8)])


@pytest.mark.parametrize("name,scale", [pytest.param(n, s, marks=needs(n)) for n, s in CASES])
def test_parse_fixture(name, scale):
    image, grid, walls = load(name)
    board = parse(scaled(image, scale))
    assert board.grid == grid
    assert norm_walls(board.walls) == norm_walls(walls)


@pytest.mark.parametrize("name", [pytest.param(n, marks=needs(n)) for n in ("hard_8x8", "walls_7x7", "walls_6x6")])
def test_end_to_end(name, tmp_path):
    out = tmp_path / "solved.png"
    main([str(FIX / f"{name}.png"), "-o", str(out)])
    assert cv2.imread(str(out)) is not None
    image, grid, walls = load(name)
    board = parse(image)
    assert is_valid(grid, solve(board.grid, board.walls), walls)
