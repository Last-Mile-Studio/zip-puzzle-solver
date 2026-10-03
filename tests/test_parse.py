from pathlib import Path

import cv2
import pytest

from zip_solver import main
from zipsolve.parse import parse
from zipsolve.solve import is_valid, solve

FIX = Path(__file__).parent / "fixtures"

# Screenshots are kept out of the repo; these tests run only where one exists locally.
pytestmark = pytest.mark.skipif(not (FIX / "hard_8x8.png").exists(), reason="fixture screenshot not present")


def load(name):
    grid = [list(map(int, l.split())) for l in open(FIX / f"{name}.txt") if l.strip()]
    return cv2.imread(str(FIX / f"{name}.png")), grid


@pytest.mark.parametrize("scale", [1.0, 0.6, 0.8, 1.5])
def test_parse_fixture_at_scales(scale):
    image, truth = load("hard_8x8")
    if scale != 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    assert parse(image).grid == truth


def test_end_to_end(tmp_path):
    out = tmp_path / "solved.png"
    main([str(FIX / "hard_8x8.png"), "-o", str(out)])
    assert cv2.imread(str(out)) is not None
    image, truth = load("hard_8x8")
    assert is_valid(truth, solve(parse(image).grid))
