import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve, delimiter } from "node:path";
const root = resolve(import.meta.dirname, "..");
const local = resolve(root, ".tools");
const env = { ...process.env };
if (process.argv[2] === "dev") env.PETRUS_DEV_ENGINE = "1";
if (existsSync(resolve(local, "cargo/bin/cargo"))) {
  env.CARGO_HOME = resolve(local, "cargo");
  env.RUSTUP_HOME = resolve(local, "rustup");
  env.PATH = `${resolve(local, "cargo/bin")}${delimiter}${env.PATH}`;
}
const result = spawnSync(
  resolve(root, "node_modules/.bin/tauri"),
  process.argv.slice(2),
  { cwd: root, env, stdio: "inherit" },
);
if (result.error) console.error(result.error.message);
if (
  result.status === 0 &&
  process.argv[2] === "build" &&
  process.platform === "darwin"
) {
  const profile = process.argv.includes("--debug") ? "debug" : "release";
  const bundle = resolve(
    root,
    "src-tauri/target",
    profile,
    "bundle/macos/PETRUS.app",
  );
  if (existsSync(bundle)) {
    // A local development signature; distribution still needs a Developer ID and notarization.
    const signed = spawnSync(
      "codesign",
      ["--force", "--deep", "--sign", "-", bundle],
      { stdio: "inherit" },
    );
    if (signed.status !== 0) process.exit(signed.status ?? 1);
    const verified = spawnSync(
      "codesign",
      ["--verify", "--deep", "--strict", bundle],
      { stdio: "inherit" },
    );
    if (verified.status !== 0) process.exit(verified.status ?? 1);
  }
}
process.exit(result.status ?? 1);
