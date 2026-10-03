# Zip solver — design

Solve LinkedIn's Zip puzzle from a phone screenshot and write an annotated image.

## Rules
N×N grid, numbered cells 1..K. Path starts at 1, visits numbers in order,
moves orthogonally, visits every cell exactly once, ends at K. Some puzzles have walls:
thick bars on cell edges the path cannot cross.

## Usage
`python zip_solver.py screenshot.png [-o out.png]` → `<name>_solved.png`,
prints the parsed grid and per-stage timings.

## Components
- `zipsolve/parse.py` — screenshot → `list[list[int]]` (0 = empty).
  Classical CV, no ML: locate grid via evenly spaced gray line projections;
  numbered cell = dark center; digits = white blobs inside the disk,
  normalized and matched against templates cut from `tests/fixtures/hard_8x8.png`.
  Walls = cell edges whose middle stretch is mostly black.
  Fails loudly unless the numbers are exactly 1..K.
- `zipsolve/solve.py` — grid + walls → list of `(r, c)` or `None`.
  Bitmask DFS with pruning: numbered cells enterable only in order,
  connectivity of unvisited cells, dead-end (degree) check, most-constrained-first ordering.
- `zipsolve/render.py` — draws the path over the original screenshot.

## Testing
Solver unit tests on small grids (solvable + unsolvable), parser test asserting
the exact grid of the fixture, end-to-end path validity check.
