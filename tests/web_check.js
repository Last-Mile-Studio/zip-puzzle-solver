// Usage: node tests/web_check.js <rgba.raw> <width> <height>
// Prints {grid, valid, solveMs} as JSON, using the same code the web page runs.
const fs = require("fs");
const path = require("path");
const Zip = require(path.join(__dirname, "..", "docs", "zip.js"));
const templates = require(path.join(__dirname, "..", "docs", "digits.js"));

const [file, w, h] = [process.argv[2], Number(process.argv[3]), Number(process.argv[4])];
const gray = Zip.toGray(fs.readFileSync(file), w, h);
const { grid } = Zip.parse(gray, w, h, templates);
const t = performance.now();
const sol = Zip.solve(grid);
const solveMs = performance.now() - t;
console.log(JSON.stringify({ grid, valid: Zip.isValid(grid, sol), solveMs }));
