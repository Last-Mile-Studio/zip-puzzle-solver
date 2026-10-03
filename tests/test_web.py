"""Check the web page's JavaScript port reads and solves the fixture like the Python code."""

import json
import shutil
import subprocess
from pathlib import Path

import cv2
import pytest

ROOT = Path(__file__).parent.parent
FIX = Path(__file__).parent / "fixtures"

pytestmark = [
    pytest.mark.skipif(not (FIX / "hard_8x8.png").exists(), reason="fixture screenshot not present"),
    pytest.mark.skipif(shutil.which("node") is None, reason="node not installed"),
]


@pytest.mark.parametrize("scale", [1.0, 0.6, 0.8, 1.5])
def test_js_matches_truth(scale, tmp_path):
    truth = [list(map(int, l.split())) for l in open(FIX / "hard_8x8.txt") if l.strip()]
    image = cv2.imread(str(FIX / "hard_8x8.png"))
    if scale != 1.0:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    h, w = image.shape[:2]
    raw = tmp_path / "img.rgba"
    raw.write_bytes(cv2.cvtColor(image, cv2.COLOR_BGR2RGBA).tobytes())
    out = subprocess.run(["node", str(ROOT / "tests" / "web_check.js"), str(raw), str(w), str(h)],
                         capture_output=True, text=True, check=True)
    result = json.loads(out.stdout)
    assert result["grid"] == truth
    assert result["valid"]
