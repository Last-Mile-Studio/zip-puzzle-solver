"""Solve a LinkedIn Zip puzzle from a screenshot.

Usage: python zip_solver.py screenshot.png [-o solved.png]
"""

import argparse
import sys
import time
from pathlib import Path

import cv2

from zipsolve.parse import ParseError, parse
from zipsolve.render import render
from zipsolve.solve import solve


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("-o", "--output", help="output path (default: <image>_solved.png)")
    args = ap.parse_args(argv)

    t0 = time.perf_counter()
    image = cv2.imread(args.image)
    if image is None:
        sys.exit(f"could not read {args.image}")
    t1 = time.perf_counter()
    try:
        board = parse(image)
    except ParseError as e:
        sys.exit(f"parse failed: {e}")
    t2 = time.perf_counter()
    path = solve(board.grid, board.walls)
    t3 = time.perf_counter()

    if board.walls:
        print(f"{len(board.walls)} wall segments")
    for row in board.grid:
        print(" ".join(f"{v:2d}" if v else " ." for v in row))
    if path is None:
        sys.exit("no solution (grid may have been misread)")

    out = args.output or str(Path(args.image).with_name(Path(args.image).stem + "_solved.png"))
    cv2.imwrite(out, render(image, board, path))
    t4 = time.perf_counter()
    ms = lambda a, b: f"{(b - a) * 1000:.1f}ms"
    print(f"load {ms(t0, t1)} | parse {ms(t1, t2)} | solve {ms(t2, t3)} | render+save {ms(t3, t4)} | total {ms(t0, t4)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
