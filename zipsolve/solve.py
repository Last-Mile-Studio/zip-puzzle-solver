"""Backtracking Zip solver over bitmasks.

Grid is a square list of lists: 0 = empty, k > 0 = numbered cell.
The path starts at 1, hits numbers in order, covers every cell once and ends at K.
"""

import sys


def solve(grid):
    n = len(grid)
    total = n * n
    flat = [v for row in grid for v in row]
    k_max = max(flat)
    pos = {v: i for i, v in enumerate(flat) if v}
    if sorted(pos) != list(range(1, k_max + 1)):
        raise ValueError(f"numbers must be exactly 1..{k_max}, got {sorted(pos)}")

    full = (1 << total) - 1
    not_left = sum(1 << (r * n + c) for r in range(n) for c in range(1, n))
    not_right = sum(1 << (r * n + c) for r in range(n) for c in range(n - 1))

    nbrs = []
    for i in range(total):
        r, c = divmod(i, n)
        nb = []
        if r > 0: nb.append(i - n)
        if r < n - 1: nb.append(i + n)
        if c > 0: nb.append(i - 1)
        if c < n - 1: nb.append(i + 1)
        nbrs.append(nb)

    numbered = 0
    for i in pos.values():
        numbered |= 1 << i
    end = pos[k_max]
    end_bit = 1 << end

    def feasible(free, cur, target):
        """Prune states that cannot be completed."""
        if not free:
            return True
        avail = free | (1 << cur)
        # The next number must be reachable without stepping on any other number.
        # (Flood fills are inlined: this is the hot loop.)
        tbit = 1 << pos[target]
        lane = (avail & ~numbered) | tbit
        f = 1 << cur
        while not f & tbit:
            nf = (f | (f << 1) & not_left | (f >> 1) & not_right | f << n | f >> n) & lane
            if nf == f:
                return False
            f = nf
        # Every free cell must be reachable from cur through free cells.
        while True:
            nf = (f | (f << 1) & not_left | (f >> 1) & not_right | f << n | f >> n) & avail
            if nf == f:
                break
            f = nf
        if free & ~f:
            return False
        # Every free cell except the end needs >= 2 available neighbours.
        a = (avail << 1) & not_left
        b = (avail >> 1) & not_right
        c = avail << n
        d = avail >> n
        two = (a & b) | (a & c) | (a & d) | (b & c) | (b & d) | (c & d)
        if free & ~two & ~end_bit:
            return False
        return True

    sys.setrecursionlimit(max(1000, total * 4))
    path = [pos[1]]

    def dfs(cur, free, target):
        if not free:
            return cur == end
        cands = []
        for j in nbrs[cur]:
            jb = 1 << j
            if not free & jb:
                continue
            if numbered & jb:
                if flat[j] != target:
                    continue
                if j == end and free != jb:
                    continue
            nfree = free & ~jb
            # Warnsdorff: fewest onward options first.
            onward = sum(1 for x in nbrs[j] if nfree >> x & 1)
            cands.append((onward, j))
        cands.sort()
        for _, j in cands:
            nfree = free & ~(1 << j)
            nt = target + 1 if flat[j] == target else target
            if not feasible(nfree, j, nt):
                continue
            path.append(j)
            if dfs(j, nfree, nt):
                return True
            path.pop()
        return False

    start = pos[1]
    free = full & ~(1 << start)
    if total == 1:
        return [(0, 0)]
    if not feasible(free, start, 2) or not dfs(start, free, 2):
        return None
    return [divmod(i, n) for i in path]


def is_valid(grid, path):
    """Check a path against the rules."""
    n = len(grid)
    if path is None or len(path) != n * n or len(set(path)) != n * n:
        return False
    for (r1, c1), (r2, c2) in zip(path, path[1:]):
        if abs(r1 - r2) + abs(c1 - c2) != 1:
            return False
    seen = [grid[r][c] for r, c in path if grid[r][c]]
    return seen == list(range(1, len(seen) + 1)) and grid[path[-1][0]][path[-1][1]] == len(seen)
