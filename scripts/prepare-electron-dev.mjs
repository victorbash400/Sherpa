import { execFileSync } from "node:child_process";
import { existsSync, renameSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const require = createRequire(import.meta.url);
const electronRoot = path.dirname(require.resolve("electron"));
const electronPlist = path.join(electronRoot, "dist", "Electron.app", "Contents", "Info.plist");
const sherpaPlist = path.join(electronRoot, "dist", "Sherpa.app", "Contents", "Info.plist");

if (!existsSync(electronPlist) && !existsSync(sherpaPlist)) {
  execFileSync(process.execPath, [path.join(electronRoot, "install.js")], { stdio: "inherit" });
}

const electronBundle = path.join(electronRoot, "dist", "Electron.app");
const sherpaBundle = path.join(electronRoot, "dist", "Sherpa.app");
let appBundle = existsSync(sherpaBundle) ? sherpaBundle : electronBundle;
let plist = path.join(appBundle, "Contents", "Info.plist");
const plistBuddy = "/usr/libexec/PlistBuddy";
let changed = false;

function read(key) {
  try {
    return execFileSync(plistBuddy, ["-c", `Print :${key}`, plist], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

function set(key, value) {
  try {
    execFileSync(plistBuddy, ["-c", `Set :${key} ${value}`, plist]);
  } catch {
    execFileSync(plistBuddy, ["-c", `Add :${key} string ${value}`, plist]);
  }
}

if (
  read("CFBundleName") !== "Sherpa"
  || read("CFBundleIdentifier") !== "com.sherpa.desktop.dev"
  || read("CFBundleExecutable") !== "Sherpa"
) {
  changed = true;
  set("CFBundleName", "Sherpa");
  set("CFBundleDisplayName", "Sherpa");
  set("CFBundleIdentifier", "com.sherpa.desktop.dev");
  const electronExecutable = path.join(appBundle, "Contents", "MacOS", "Electron");
  const sherpaExecutable = path.join(appBundle, "Contents", "MacOS", "Sherpa");
  if (existsSync(electronExecutable)) renameSync(electronExecutable, sherpaExecutable);
  set("CFBundleExecutable", "Sherpa");
  if (appBundle === electronBundle) {
    renameSync(electronBundle, sherpaBundle);
    appBundle = sherpaBundle;
    plist = path.join(appBundle, "Contents", "Info.plist");
  }
}

writeFileSync(path.join(electronRoot, "path.txt"), "Sherpa.app/Contents/MacOS/Sherpa");
if (changed) {
  execFileSync("codesign", ["--force", "--deep", "--sign", "-", appBundle], { stdio: "inherit" });
}
