"""Draw a solution path over the original screenshot."""

import cv2
import numpy as np

PATH_BGR = (60, 140, 255)  # orange
START_BGR = (80, 175, 76)  # green


def render(image, board, path):
    out = image.copy()
    overlay = image.copy()
    cell = board.xs[1] - board.xs[0]
    pts = np.array([board.center(r, c) for r, c in path], np.int32)
    thick = max(2, int(cell * 0.3))
    cv2.polylines(overlay, [pts], False, PATH_BGR, thick, lineType=cv2.LINE_AA)
    for p in pts:  # round the corners
        cv2.circle(overlay, tuple(int(v) for v in p), thick // 2, PATH_BGR, -1, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.65, out, 0.35, 0, out)
    # Put the number disks back on top so they stay readable.
    disks = np.zeros(image.shape[:2], np.uint8)
    for r, row in enumerate(board.grid):
        for c, v in enumerate(row):
            if v:
                cx, cy = board.center(r, c)
                cv2.circle(disks, (int(cx), int(cy)), int(cell * 0.37), 255, -1)
    out[disks > 0] = image[disks > 0]
    cv2.circle(out, tuple(int(v) for v in pts[0]), int(cell * 0.42), START_BGR, max(2, int(cell * 0.06)), cv2.LINE_AA)
    return out
