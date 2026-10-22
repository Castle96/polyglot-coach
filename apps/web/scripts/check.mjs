// Lightweight static checks for the bundled web client.
//
// The client is a single hand-written index.html with no build step, so there
// is no bundler or transpiler to catch mistakes. This script covers the failure
// modes that actually bite here: a selector in the markup that the script
// expects but that is missing, and a script that references an element id the
// markup never defines.
//
// Run with `npm run lint` (check only) or `npm run format` (report only; there
// is no autofix because the file is hand-formatted).

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const htmlPath = join(here, "..", "index.html");
const html = readFileSync(htmlPath, "utf8");

const scriptMatch = html.match(/<script>([\s\S]*?)<\/script>/);
const styleMatch = html.match(/<style>([\s\S]*?)<\/style>/);

if (!scriptMatch) {
  console.error("index.html: no <script> block found");
  process.exit(1);
}
if (!styleMatch) {
  console.error("index.html: no <style> block found");
  process.exit(1);
}

const script = scriptMatch[1];
const markup = html.replace(/<script>[\s\S]*?<\/script>/, "").replace(/<style>[\s\S]*?<\/style>/, "");

const problems = [];

// 1. Every getElementById target must exist as an id in the markup.
const idRefs = [...script.matchAll(/getElementById\(\s*["'`]([^"'`]+)["'`]\s*\)/g)].map((m) => m[1]);
for (const id of new Set(idRefs)) {
  const defined = new RegExp(`id=["'\`]${id}["'\`]`).test(markup);
  if (!defined) {
    problems.push(`getElementById("${id}") has no matching id in the markup`);
  }
}

// 2. Every querySelector/querySelectorAll target must exist in the markup.
const selectorRefs = [
  ...script.matchAll(/querySelector(?:All)?\(\s*["'`]([^"'`]+)["'`]\s*\)/g),
].map((m) => m[1]);
for (const selector of new Set(selectorRefs)) {
  const bare = selector.replace(/^[.#]/, "").split(/[ >:[]/)[0];
  if (!bare) continue;
  const defined = selector.startsWith("#")
    ? new RegExp(`id=["'\`]${bare}["'\`]`).test(markup)
    : new RegExp(`class=["'\`][^"'\`]*\\b${bare}\\b`).test(markup);
  if (!defined) {
    problems.push(`querySelector("${selector}") matches nothing in the markup`);
  }
}

// 3. Every fetch path must be a route the API actually serves.
const knownRoutes = [
  "/health",
  "/api/v1/meta/languages",
  "/api/v1/curriculum/lessons",
  "/api/v1/learner/profiles",
  "/api/v1/speech/transcribe",
  "/api/v1/speech/synthesize",
  "/api/v1/tutor/chat",
];
const fetchRefs = [...script.matchAll(/fetch\(\s*[`'"]([^`'"]+)/g)].map((m) => m[1]);
for (const ref of new Set(fetchRefs)) {
  const path = ref.replace(/\$\{[^}]*\}/g, "").split("?")[0];
  if (!knownRoutes.some((route) => path === route || path.startsWith(route + "/"))) {
    problems.push(`fetch("${ref}") targets an unknown API route`);
  }
}

// 4. Balanced tags for the structural elements the script depends on.
for (const tag of ["html", "head", "body", "style", "script"]) {
  const open = (html.match(new RegExp(`<${tag}[\\s>]`, "g")) || []).length;
  const close = (html.match(new RegExp(`</${tag}>`, "g")) || []).length;
  if (open !== close) {
    problems.push(`<${tag}> opened ${open} times but closed ${close} times`);
  }
}

if (problems.length) {
  console.error(`index.html: ${problems.length} problem(s) found`);
  for (const problem of problems) {
    console.error(`  - ${problem}`);
  }
  process.exit(1);
}

console.log(`index.html: ${new Set(idRefs).size} element ids, ${new Set(selectorRefs).size} selectors, ${new Set(fetchRefs).size} fetch calls — all resolve`);
