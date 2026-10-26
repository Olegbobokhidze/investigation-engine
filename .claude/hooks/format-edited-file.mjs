// PostToolUse hook: formats the file Claude just edited, so every change already matches
// the project's formatters (ruff for apps/api, Prettier for apps/web) before CI sees it.
//
// Input: the hook event as JSON on stdin; we only need `tool_input.file_path`.
// Exit 0 on success or when the file isn't ours to format; exit 1 (non-blocking) and print
// the formatter's error when formatting fails, so it shows up in the transcript.
import { spawnSync } from "node:child_process";
import path from "node:path";

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

function isInside(directory, filePath) {
  const relative = path.relative(directory, filePath);
  return relative !== "" && !relative.startsWith("..") && !path.isAbsolute(relative);
}

const event = JSON.parse(await readStdin());
const filePath = event.tool_input?.file_path;
if (typeof filePath !== "string") process.exit(0);

const projectDir = process.env.CLAUDE_PROJECT_DIR ?? process.cwd();
const apiDir = path.join(projectDir, "apps", "api");
const webDir = path.join(projectDir, "apps", "web");

/** @type {Array<[string, string[]]>} */
let commands = [];
if (isInside(apiDir, filePath) && filePath.endsWith(".py")) {
  const ruff = ["--directory", apiDir, "run", "ruff"];
  commands = [
    ["uv", [...ruff, "format", "--quiet", filePath]],
    // Only sorts imports (rule I). A full `--fix` would delete an import added one edit
    // before the code that uses it; other issues are reported by `make api-check`.
    ["uv", [...ruff, "check", "--select", "I", "--fix", "--exit-zero", "--quiet", filePath]],
  ];
} else if (isInside(webDir, filePath) && /\.(ts|tsx|js|css|json|html|md)$/.test(filePath)) {
  commands = [
    ["pnpm", ["--dir", webDir, "exec", "prettier", "--write", "--log-level", "warn", filePath]],
  ];
}

for (const [command, args] of commands) {
  const result = spawnSync(command, args, { encoding: "utf8" });
  if (result.status !== 0) {
    console.error(`${command} failed to format ${filePath}:\n${result.stderr || result.stdout}`);
    process.exit(1);
  }
}
