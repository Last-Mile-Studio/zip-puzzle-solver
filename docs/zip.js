// Zip puzzle reader + solver. Port of zipsolve/parse.py and zipsolve/solve.py.
// Works in the browser (globals) and in Node (module.exports) for testing.

const ZipCore = (() => {
  const GLYPH = 24;

  class ParseError extends Error {}

  // ---------- image helpers ----------

  function toGray(rgba, w, h) {
    const g = new Uint8Array(w * h);
    for (let i = 0, j = 0; i < g.length; i++, j += 4) {
      g[i] = Math.round(0.299 * rgba[j] + 0.587 * rgba[j + 1] + 0.114 * rgba[j + 2]);
    }
    return g;
  }

  // Label 8-connected components of mask (Uint8Array, 1 = set). Returns {labels, areas, minX}.
  function components(mask, w, h) {
    const labels = new Int32Array(w * h);
    const areas = [0], minX = [0];
    const stack = new Int32Array(w * h);
    let next = 1;
    for (let start = 0; start < mask.length; start++) {
      if (!mask[start] || labels[start]) continue;
      let sp = 0, area = 0, mx = w;
      stack[sp++] = start;
      labels[start] = next;
      while (sp) {
        const p = stack[--sp];
        area++;
        const x = p % w, y = (p - x) / w;
        if (x < mx) mx = x;
        for (let dy = -1; dy <= 1; dy++) {
          const yy = y + dy;
          if (yy < 0 || yy >= h) continue;
          for (let dx = -1; dx <= 1; dx++) {
            const xx = x + dx;
            if (xx < 0 || xx >= w) continue;
            const q = yy * w + xx;
            if (mask[q] && !labels[q]) { labels[q] = next; stack[sp++] = q; }
          }
        }
      }
      areas.push(area);
      minX.push(mx);
      next++;
    }
    return { labels, areas, minX };
  }

  // ---------- grid detection ----------

  function lineCenters(profile, thresh) {
    const out = [];
    let group = [];
    for (let i = 0; i < profile.length; i++) {
      if (profile[i] < thresh) continue;
      if (group.length && i - group[group.length - 1] > 2) {
        out.push(group.reduce((a, b) => a + b, 0) / group.length);
        group = [];
      }
      group.push(i);
    }
    if (group.length) out.push(group.reduce((a, b) => a + b, 0) / group.length);
    return out;
  }

  // Cell size: the gap that explains the most gaps as whole multiples of itself.
  // Walls can hide grid lines, so some gaps are 2x or 3x the real spacing.
  function estimateSpacing(pos, minSpacing) {
    const gaps = pos.slice(1).map((v, i) => v - pos[i]).filter((g) => g >= minSpacing);
    if (!gaps.length) throw new ParseError("Couldn't find the puzzle grid in this image.");
    const fits = (g) => gaps.filter((x) => Math.abs(x / g - Math.round(x / g)) * g <= 0.15 * g).length;
    let best = null, bestFits = -1;
    for (const g of [...gaps].sort((x, y) => x - y)) {  // ties go to the smallest gap
      const f = fits(g);
      if (f > bestFits) { bestFits = f; best = g; }
    }
    return best;
  }

  // Longest run of positions spaced `spacing` apart (within tol). A gap of 2-4x spacing is
  // bridged when the profile shows some line at each missing position: a wall lying on a
  // grid line hides part of it.
  function longestEvenChain(pos, spacing, tol, profile, minEvidence) {
    const evidence = (p) => {
      const r = Math.max(1, Math.floor(0.05 * spacing));
      let m = 0;
      for (let i = Math.max(0, Math.floor(p) - r); i <= Math.floor(p) + r && i < profile.length; i++) m = Math.max(m, profile[i]);
      return m;
    };
    let best = [];
    for (let i = 0; i < pos.length; i++) {
      const chain = [pos[i]];
      for (const p of pos.slice(i + 1)) {
        const last = chain[chain.length - 1], gap = p - last;
        const k = Math.round(gap / spacing);
        if (k < 1 || Math.abs(gap - k * spacing) > tol * k) {
          if (gap > 4 * spacing + tol) break;
          continue;
        }
        const missing = [];
        for (let j = 1; j < k; j++) missing.push(last + (gap * j) / k);
        if (k > 4 || missing.some((m) => evidence(m) < minEvidence)) break;
        chain.push(...missing, p);
      }
      if (chain.length > best.length) best = chain;
    }
    return best;
  }

  function findGrid(gray, w, h) {
    const isLine = (v) => v > 100 && v < 225;
    const col = new Float64Array(w);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (isLine(gray[y * w + x])) col[x]++;
    let colMax = 0;
    for (const v of col) colMax = Math.max(colMax, v);
    let xs = lineCenters(col, 0.6 * colMax);
    if (xs.length < 3) throw new ParseError("Couldn't find the puzzle grid in this image.");
    const spacing = estimateSpacing(xs, 0.04 * w);
    xs = longestEvenChain(xs, spacing, 0.15 * spacing, col, 0.1 * colMax);

    const x0 = Math.floor(xs[0]), x1 = Math.floor(xs[xs.length - 1]);
    const row = new Float64Array(h);
    for (let y = 0; y < h; y++) for (let x = x0; x < x1; x++) if (isLine(gray[y * w + x])) row[y]++;
    let ys = lineCenters(row, 0.6 * (x1 - x0));
    ys = longestEvenChain(ys, spacing, 0.15 * spacing, row, 0.1 * (x1 - x0));

    const n = xs.length - 1;
    if (n < 2 || ys.length !== n + 1) {
      throw new ParseError("Couldn't find the puzzle grid in this image.");
    }
    return { xs, ys };
  }

  // ---------- digits ----------

  // Area-average resize of a side x side binary square to GLYPH x GLYPH.
  function resizeArea(sq, side) {
    const out = new Float32Array(GLYPH * GLYPH);
    const s = side / GLYPH;
    for (let oy = 0; oy < GLYPH; oy++) {
      const y0 = oy * s, y1 = y0 + s;
      for (let ox = 0; ox < GLYPH; ox++) {
        const x0 = ox * s, x1 = x0 + s;
        let sum = 0, wsum = 0;
        for (let y = Math.floor(y0); y < Math.ceil(y1) && y < side; y++) {
          const wy = Math.min(y + 1, y1) - Math.max(y, y0);
          for (let x = Math.floor(x0); x < Math.ceil(x1) && x < side; x++) {
            const wx = Math.min(x + 1, x1) - Math.max(x, x0);
            sum += sq[y * side + x] * wx * wy;
            wsum += wx * wy;
          }
        }
        out[oy * GLYPH + ox] = wsum ? sum / wsum : 0;
      }
    }
    return out;
  }

  function normalizeGlyph(labels, label, w, h) {
    let minX = w, maxX = -1, minY = h, maxY = -1;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      if (labels[y * w + x] !== label) continue;
      if (x < minX) minX = x; if (x > maxX) maxX = x;
      if (y < minY) minY = y; if (y > maxY) maxY = y;
    }
    const gw = maxX - minX + 1, gh = maxY - minY + 1, side = Math.max(gw, gh);
    const sq = new Uint8Array(side * side);
    const ox = (side - gw) >> 1, oy = (side - gh) >> 1;
    for (let y = 0; y < gh; y++) for (let x = 0; x < gw; x++) {
      if (labels[(minY + y) * w + minX + x] === label) sq[(oy + y) * side + ox + x] = 1;
    }
    return resizeArea(sq, side);
  }

  // Returns normalized glyphs (left to right) if the cell holds a number disk, else null.
  function cellGlyphs(cell, w, h) {
    const size = w * h;
    const dark = new Uint8Array(size);
    for (let i = 0; i < size; i++) if (cell[i] < 110) dark[i] = 1;
    // Judge by the middle of the cell so wall bars along the edges don't count.
    const qy = h >> 2, qx = w >> 2;
    let coreDark = 0, coreSize = 0;
    for (let y = qy; y < h - qy; y++) for (let x = qx; x < w - qx; x++) { coreDark += dark[y * w + x]; coreSize++; }
    if (coreDark / coreSize < 0.3) return null;

    // The disk is the dark component covering most of the middle (walls never reach it).
    const dc = components(dark, w, h);
    const votes = new Map();
    for (let y = qy; y < h - qy; y++) for (let x = qx; x < w - qx; x++) {
      const l = dc.labels[y * w + x];
      if (l) votes.set(l, (votes.get(l) || 0) + 1);
    }
    let diskLabel = 0, bestVotes = -1;
    for (const [l, v] of votes) if (v > bestVotes || (v === bestVotes && l < diskLabel)) { bestVotes = v; diskLabel = l; }

    // Fill its holes: anything not reachable from the border without crossing the disk.
    const outside = new Uint8Array(size);
    const stack = new Int32Array(size);
    let sp = 0;
    const seed = (p) => { if (!outside[p] && dc.labels[p] !== diskLabel) { outside[p] = 1; stack[sp++] = p; } };
    for (let x = 0; x < w; x++) { seed(x); seed((h - 1) * w + x); }
    for (let y = 0; y < h; y++) { seed(y * w); seed(y * w + w - 1); }
    while (sp) {
      const p = stack[--sp];
      const x = p % w;
      if (x > 0) seed(p - 1);
      if (x < w - 1) seed(p + 1);
      if (p >= w) seed(p - w);
      if (p < size - w) seed(p + w);
    }

    // Erode the filled disk 5x5 to drop its anti-aliased rim (image border doesn't erode).
    const tmp = new Uint8Array(size), disk = new Uint8Array(size);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let ok = 1;
      for (let dx = -2; dx <= 2 && ok; dx++) {
        const xx = x + dx;
        if (xx >= 0 && xx < w && outside[y * w + xx]) ok = 0;
      }
      tmp[y * w + x] = ok;
    }
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let ok = 1;
      for (let dy = -2; dy <= 2 && ok; dy++) {
        const yy = y + dy;
        if (yy >= 0 && yy < h && !tmp[yy * w + x]) ok = 0;
      }
      disk[y * w + x] = ok;
    }

    const white = new Uint8Array(size);
    for (let i = 0; i < size; i++) if (disk[i] && cell[i] > 150) white[i] = 1;
    const wc = components(white, w, h);
    const minArea = 0.004 * size;
    const blobs = [];
    for (let i = 1; i < wc.areas.length; i++) if (wc.areas[i] >= minArea) blobs.push(i);
    if (!blobs.length) throw new ParseError("Found a number circle with no digits in it.");
    blobs.sort((a, b) => wc.minX[a] - wc.minX[b]);
    return blobs.map((b) => normalizeGlyph(wc.labels, b, w, h));
  }

  function classify(glyph, templates) {
    let best = null, bestD = Infinity;
    for (const d in templates) {
      const t = templates[d];
      let dist = 0;
      for (let i = 0; i < t.length; i++) dist += Math.abs(t[i] - glyph[i]);
      if (dist < bestD) { bestD = dist; best = d; }
    }
    return best;
  }

  // Edges whose middle stretch is mostly black are walls. Returns [[[r1, c1], [r2, c2]], ...].
  function findWalls(gray, w, xs, ys) {
    const n = xs.length - 1, walls = [];
    const darkFrac = (x0, x1, y0, y1) => {
      let d = 0, tot = 0;
      for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) { tot++; if (gray[y * w + x] < 80) d++; }
      return tot ? d / tot : 0;
    };
    for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
      const s = xs[c + 1] - xs[c], t = Math.max(1, Math.round(0.06 * s));
      if (c + 1 < n) {
        const x = Math.round(xs[c + 1]);
        if (darkFrac(x - t, x + t + 1, Math.floor(ys[r] + 0.25 * s), Math.floor(ys[r + 1] - 0.25 * s)) > 0.5) walls.push([[r, c], [r, c + 1]]);
      }
      if (r + 1 < n) {
        const y = Math.round(ys[r + 1]);
        if (darkFrac(Math.floor(xs[c] + 0.25 * s), Math.floor(xs[c + 1] - 0.25 * s), y - t, y + t + 1) > 0.5) walls.push([[r, c], [r + 1, c]]);
      }
    }
    return walls;
  }

  function parse(gray, w, h, templates) {
    const { xs, ys } = findGrid(gray, w, h);
    const n = xs.length - 1;
    const grid = Array.from({ length: n }, () => new Array(n).fill(0));
    for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) {
      const mx = Math.floor(0.08 * (xs[c + 1] - xs[c]));
      const my = Math.floor(0.08 * (ys[r + 1] - ys[r]));
      const cx0 = Math.floor(xs[c]) + mx, cx1 = Math.floor(xs[c + 1]) - mx;
      const cy0 = Math.floor(ys[r]) + my, cy1 = Math.floor(ys[r + 1]) - my;
      const cw = cx1 - cx0, ch = cy1 - cy0;
      const cell = new Uint8Array(cw * ch);
      for (let y = 0; y < ch; y++) for (let x = 0; x < cw; x++) cell[y * cw + x] = gray[(cy0 + y) * w + cx0 + x];
      const glyphs = cellGlyphs(cell, cw, ch);
      if (glyphs) grid[r][c] = Number(glyphs.map((g) => classify(g, templates)).join(""));
    }
    const nums = grid.flat().filter(Boolean).sort((a, b) => a - b);
    if (!nums.every((v, i) => v === i + 1)) {
      const err = new ParseError(`Misread the numbers (expected 1–${nums.length}).`);
      err.grid = grid;
      throw err;
    }
    return { grid, xs, ys, walls: findWalls(gray, w, xs, ys) };
  }

  // ---------- solver ----------

  // Returns [[r, c], ...] from 1 to K covering every cell without crossing a wall, or null.
  function solve(grid, walls = []) {
    const n = grid.length, total = n * n;
    const flat = grid.flat();
    const kMax = Math.max(...flat);
    const pos = new Int32Array(kMax + 2).fill(-1);
    flat.forEach((v, i) => { if (v) pos[v] = i; });
    const end = pos[kMax];

    const blocked = new Set(walls.map(([[r1, c1], [r2, c2]]) => {
      const a = r1 * n + c1, b = r2 * n + c2;
      return Math.min(a, b) * total + Math.max(a, b);
    }));
    const open = (a, b) => !blocked.has(Math.min(a, b) * total + Math.max(a, b));
    const nbrs = [];
    for (let i = 0; i < total; i++) {
      const r = Math.floor(i / n), c = i % n, nb = [];
      if (r > 0 && open(i, i - n)) nb.push(i - n);
      if (r < n - 1 && open(i, i + n)) nb.push(i + n);
      if (c > 0 && open(i, i - 1)) nb.push(i - 1);
      if (c < n - 1 && open(i, i + 1)) nb.push(i + 1);
      nbrs.push(nb);
    }

    const free = new Uint8Array(total).fill(1);
    const seen = new Int32Array(total);
    const queue = new Int32Array(total);
    let stamp = 0;

    // Same pruning as the Python solver.
    function feasible(cur, target, freeCount) {
      if (!freeCount) return true;
      // Next number reachable without stepping on another number.
      const goal = pos[target];
      stamp++;
      let qh = 0, qt = 0, found = false;
      queue[qt++] = cur; seen[cur] = stamp;
      while (qh < qt && !found) {
        for (const j of nbrs[queue[qh++]]) {
          if (seen[j] === stamp || !free[j]) continue;
          if (j === goal) { found = true; break; }
          if (flat[j]) continue;
          seen[j] = stamp; queue[qt++] = j;
        }
      }
      if (!found) return false;
      // All free cells connected to cur.
      stamp++;
      qh = 0; qt = 0;
      queue[qt++] = cur; seen[cur] = stamp;
      let reached = 0;
      while (qh < qt) {
        for (const j of nbrs[queue[qh++]]) {
          if (seen[j] === stamp || !free[j]) continue;
          seen[j] = stamp; queue[qt++] = j; reached++;
        }
      }
      if (reached !== freeCount) return false;
      // Every free cell except the end needs >= 2 open neighbours (free or cur).
      for (let i = 0; i < total; i++) {
        if (!free[i] || i === end) continue;
        let deg = 0;
        for (const j of nbrs[i]) if (free[j] || j === cur) deg++;
        if (deg < 2) return false;
      }
      return true;
    }

    const path = [pos[1]];
    function dfs(cur, target, freeCount) {
      if (!freeCount) return cur === end;
      const cands = [];
      for (const j of nbrs[cur]) {
        if (!free[j]) continue;
        if (flat[j]) {
          if (flat[j] !== target) continue;
          if (j === end && freeCount !== 1) continue;
        }
        free[j] = 0;
        let onward = 0;
        for (const x of nbrs[j]) if (free[x]) onward++;
        free[j] = 1;
        cands.push([onward, j]);
      }
      cands.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      for (const [, j] of cands) {
        free[j] = 0;
        const nt = flat[j] === target ? target + 1 : target;
        if (feasible(j, nt, freeCount - 1)) {
          path.push(j);
          if (dfs(j, nt, freeCount - 1)) return true;
          path.pop();
        }
        free[j] = 1;
      }
      return false;
    }

    if (total === 1) return [[0, 0]];
    free[pos[1]] = 0;
    if (!feasible(pos[1], 2, total - 1) || !dfs(pos[1], 2, total - 1)) return null;
    return path.map((i) => [Math.floor(i / n), i % n]);
  }

  function isValid(grid, path, walls = []) {
    const n = grid.length;
    const key = (r1, c1, r2, c2) => [r1 * n + c1, r2 * n + c2].sort((a, b) => a - b).join(",");
    const blocked = new Set(walls.map(([[r1, c1], [r2, c2]]) => key(r1, c1, r2, c2)));
    if (!path || path.length !== n * n) return false;
    if (new Set(path.map(([r, c]) => r * n + c)).size !== n * n) return false;
    for (let i = 1; i < path.length; i++) {
      const [r1, c1] = path[i - 1], [r2, c2] = path[i];
      if (Math.abs(r1 - r2) + Math.abs(c1 - c2) !== 1 || blocked.has(key(r1, c1, r2, c2))) return false;
    }
    const seq = path.map(([r, c]) => grid[r][c]).filter(Boolean);
    return seq.every((v, i) => v === i + 1) && grid[path[n * n - 1][0]][path[n * n - 1][1]] === seq.length;
  }

  return { ParseError, toGray, parse, solve, isValid };
})();

if (typeof module !== "undefined") module.exports = ZipCore;
