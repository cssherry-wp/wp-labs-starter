#!/usr/bin/env node
// PreToolUse hook: deterministically inject the team coding standard that matches
// the file being edited. Reads the existing skill SKILL.md files (single source of
// truth) rather than maintaining a duplicate copy of the standards.
//
// Runs on `node`, which is guaranteed present wherever Claude Code runs — no jq or
// other external dependency.
//
// SQL is intentionally NOT handled here: the .sql extension is an unreliable signal
// (SQL is frequently embedded in .py/.ts and migration files), so sql-style stays a
// normal model-invoked skill rather than a deterministic file-type trigger.
//
// On any error or non-match the hook exits 0 with no output, so it never blocks an edit.

const fs = require("fs");
const path = require("path");

// Map file extension (lowercased) to the matching skill directory.
const EXT_TO_SKILL = {
  py: "python-style",
  ts: "typescript-style",
  tsx: "typescript-style",
  js: "typescript-style",
  jsx: "typescript-style",
  mjs: "typescript-style",
  cjs: "typescript-style",
  css: "css-style",
  scss: "css-style",
  sass: "css-style",
};

try {
  const input = JSON.parse(fs.readFileSync(0, "utf8"));
  const filePath = input?.tool_input?.file_path || "";
  if (!filePath) process.exit(0);

  const ext = filePath.split(".").pop().toLowerCase();
  const skill = EXT_TO_SKILL[ext];
  if (!skill) process.exit(0); // no deterministic standard for this type

  const skillFile = path.join(__dirname, "..", "skills", skill, "SKILL.md");
  if (!fs.existsSync(skillFile)) process.exit(0);

  // Strip the leading YAML frontmatter (--- ... ---) and keep the body.
  const body = fs.readFileSync(skillFile, "utf8").replace(/^---\n[\s\S]*?\n---\n/, "");

  const additionalContext =
    `Team coding standards apply to this file (${skill}). Follow them when editing:\n\n` + body;

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        additionalContext,
      },
    })
  );
} catch {
  // Never break an edit because of a hook error.
  process.exit(0);
}
