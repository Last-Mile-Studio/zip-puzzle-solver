"""Check the web page's JavaScript port behaves like the Python code."""

import json
import random
import shutil
import subprocess
from pathlib import Path

import cv2
import pytest

from test_parse import FIX, load, needs, norm_walls, scaled
from test_solve import brute_force_solvable

ROOT = Path(__file__).parent.parent

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

CASES = [("hard_8x8", s) for s in (1.0, 0.6, 0.8, 1.5)] + [("walls_7x7", s) for s in (1.0, 1.5, 3.0)]


@pytest.mark.parametrize("name,scale", [pytest.param(n, s, marks=needs(n)) for n, s in CASES])
def test_js_reads_fixture(name, scale, tmp_path):
    image, grid, walls = load(name)
    image = scaled(image, scale)
    h, w = image.shape[:2]
    raw = tmp_path / "img.rgba"
    raw.write_bytes(cv2.cvtColor(image, cv2.COLOR_BGR2RGBA).tobytes())
    out = subprocess.run(["node", str(ROOT / "tests" / "web_check.js"), str(raw), str(w), str(h)],
                         capture_output=True, text=True, check=True)
    result = json.loads(out.stdout)
    assert result["grid"] == grid
    assert norm_walls(result["walls"]) == norm_walls(walls)
    assert result["valid"]


def test_js_solver_matches_brute_force():
    cases = []
    for seed in range(300):
        rng = random.Random(seed)
        n = rng.choice([3, 4])
        cells = [(r, c) for r in range(n) for c in range(n)]
        grid = [[0] * n for _ in range(n)]
        for v, (r, c) in enumerate(rng.sample(cells, rng.randint(2, 5)), 1):
            grid[r][c] = v
        edges = [((r, c), (r, c + 1)) for r in range(n) for c in range(n - 1)]
        edges += [((r, c), (r + 1, c)) for r in range(n - 1) for c in range(n)]
        cases.append((grid, rng.sample(edges, rng.randint(0, 4))))
    out = subprocess.run(["node", str(ROOT / "tests" / "web_solve_check.js")], check=True,
                         input=json.dumps([{"grid": g, "walls": w} for g, w in cases]),
                         capture_output=True, text=True)
    for (grid, walls), res in zip(cases, json.loads(out.stdout)):
        assert res["solved"] == brute_force_solvable(grid, walls), (grid, walls)
        assert res["valid"] == res["solved"]
