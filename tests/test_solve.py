import random

import pytest

from zipsolve.solve import is_valid, solve


def test_2x2():
    grid = [[1, 0], [2, 0]]
    assert solve(grid) == [(0, 0), (0, 1), (1, 1), (1, 0)]


def test_3x3_snake():
    grid = [[1, 0, 0], [0, 0, 0], [0, 0, 2]]
    assert is_valid(grid, solve(grid))


def test_ordering_constraint():
    grid = [[1, 0, 0], [0, 0, 2], [3, 0, 0]]
    assert is_valid(grid, solve(grid))


def test_unsolvable_parity():
    # Checkerboard colouring: a path covering an even board must end on the opposite colour.
    assert solve([[1, 0], [0, 2]]) is None
    assert solve([[1, 0, 0], [0, 0, 0], [0, 2, 0]]) is None


def test_is_valid_rejects_bad_paths():
    grid = [[1, 0], [2, 0]]
    assert not is_valid(grid, [(0, 0), (1, 1), (0, 1), (1, 0)])  # diagonal move
    assert not is_valid(grid, [(0, 0), (1, 0), (1, 1), (0, 1)])  # ends off K
    assert not is_valid(grid, None)


def test_wall_blocks_only_solution():
    grid = [[1, 0], [2, 0]]
    assert solve(grid, walls=[((0, 1), (1, 1))]) is None


def brute_force_solvable(grid, walls):
    n = len(grid)
    blocked = {frozenset(w) for w in walls}
    start = next((r, c) for r in range(n) for c in range(n) if grid[r][c] == 1)

    def go(cell, seen, path):
        if len(path) == n * n:
            return is_valid(grid, path, walls)
        r, c = cell
        for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nb[0] < n and 0 <= nb[1] < n and nb not in seen and frozenset((cell, nb)) not in blocked:
                seen.add(nb); path.append(nb)
                if go(nb, seen, path):
                    return True
                seen.discard(nb); path.pop()
        return False

    return go(start, {start}, [start])


@pytest.mark.parametrize("seed", range(300))
def test_matches_brute_force_with_random_walls(seed):
    rng = random.Random(seed)
    n = rng.choice([3, 4])
    cells = [(r, c) for r in range(n) for c in range(n)]
    k = rng.randint(2, 5)
    grid = [[0] * n for _ in range(n)]
    for v, (r, c) in enumerate(rng.sample(cells, k), 1):
        grid[r][c] = v
    edges = [((r, c), (r, c + 1)) for r in range(n) for c in range(n - 1)]
    edges += [((r, c), (r + 1, c)) for r in range(n - 1) for c in range(n)]
    walls = rng.sample(edges, rng.randint(0, 4))
    path = solve(grid, walls)
    assert (path is not None) == brute_force_solvable(grid, walls)
    if path is not None:
        assert is_valid(grid, path, walls)


def test_is_valid_rejects_wall_crossing():
    grid = [[1, 0], [2, 0]]
    assert not is_valid(grid, [(0, 0), (0, 1), (1, 1), (1, 0)], [((0, 1), (1, 1))])
