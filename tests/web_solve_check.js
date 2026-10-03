// Reads [{grid, walls}, ...] JSON on stdin; prints [{solved, valid}, ...] using the web page's solver.
const path = require("path");
const Zip = require(path.join(__dirname, "..", "docs", "zip.js"));

let input = "";
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
  const out = JSON.parse(input).map(({ grid, walls }) => {
    const sol = Zip.solve(grid, walls);
    return { solved: sol !== null, valid: sol !== null && Zip.isValid(grid, sol, walls) };
  });
  console.log(JSON.stringify(out));
});
