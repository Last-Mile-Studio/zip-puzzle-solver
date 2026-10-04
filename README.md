# zip-puzzle-solver

Solves [Zip](https://www.linkedin.com/games/zip/), the daily path puzzle on LinkedIn, from a screenshot.

Give it a screenshot, and it reads the grid with plain image processing (no ML),
finds the path from 1 to N that fills every cell (without crossing any walls) with a pruned backtracking search, and
writes the screenshot back out with the solution drawn on it. About 100 ms end to end.

**Web version:** https://last-mile-studio.github.io/zip-puzzle-solver/. Paste a screenshot
(on iPhone: screenshot → tap preview → Copy and Delete → Paste). It runs entirely in your
browser; nothing is uploaded. The page lives in `docs/` and is a JavaScript port of the
Python code. `tests/test_web.py` checks that both read the same grid.

```
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python zip_solver.py screenshot.png      # -> screenshot_solved.png
```

## How it works
- `zipsolve/parse.py`: finds the evenly spaced grid lines, detects the black number disks,
  matches each digit against templates in `zipsolve/digits.npz`, and finds walls (thick black
  bars along cell edges).
- `zipsolve/solve.py`: depth-first search over a bitmask. It drops a branch when the
  next number becomes unreachable, the free cells split apart, or a cell is left with
  fewer than two exits.
- `zipsolve/render.py`: draws the path over the original image.

If digits are misread, put a screenshot and its true grid in `tests/fixtures/` and rebuild
the templates with `tools/make_templates.py`.

Tests: `.venv/bin/python -m pytest`. The parser tests need a local screenshot in
`tests/fixtures/` (not committed) and are skipped without one.

---
Not affiliated with or endorsed by LinkedIn. Zip is a trademark of LinkedIn.
