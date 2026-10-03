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
