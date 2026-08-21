import { app, BrowserWindow, dialog, ipcMain, screen, shell } from "electron";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

app.setName("Sherpa");

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const preloadPath = path.join(currentDirectory, "preload.cjs");
const developmentServerUrl = process.env.SHERPA_DEV_SERVER_URL;
const isDevelopment = Boolean(developmentServerUrl);
const dockIconPath = !isDevelopment
  ? path.join(currentDirectory, "../dist/sherpa-dock-icon.png")
  : path.join(app.getAppPath(), "public/sherpa-dock-icon.png");
let mainWindow: BrowserWindow | undefined;
const overlayWindows = new Map<number, BrowserWindow>();
const readyOverlayDisplays = new Set<number>();
const pendingOverlays = new Map<number, OverlayPayload>();
let petWindow: BrowserWindow | undefined;
let petWorking = false;
let petTranscript: PetTranscriptPayload = { entries: [], hue: 0, status: "idle" };
let lastOverlayPoint: { x: number; y: number } | undefined;
let previewProcess: ChildProcessWithoutNullStreams | undefined;
let backendProcess: ChildProcessWithoutNullStreams | undefined;
let backendStopTimer: ReturnType<typeof setTimeout> | undefined;
let previewTaskId: string | undefined;
let previewTarget: string | undefined;
let previewBuffer = Buffer.alloc(0);
let previewStopping = false;
let previewTerminateTimer: ReturnType<typeof setTimeout> | undefined;
let previewKillTimer: ReturnType<typeof setTimeout> | undefined;
let pendingPreview: { taskId: string; target: PreviewTarget; targetKey: string } | undefined;

type OverlayPayload = {
  id: string;
  action: string;
  message: string;
  intent?: string;
  args: Record<string, unknown>;
};

type PreviewTarget = {
  app?: string;
  pid?: number;
  window_id?: number;
  window_title?: string;
};

type PetTranscriptPayload = {
  entries: Array<{ id: string; role: "user" | "assistant"; text: string }>;
  hue: number;
  status: string;
};

const PET_WIDTH = 340;
const PET_HEIGHT = 360;

function createWindow() {
  const window = new BrowserWindow({
    width: 720,
    height: 480,
    minWidth: 640,
    minHeight: 420,
    maxWidth: 760,
    maxHeight: 520,
    backgroundColor: "#ffffff",
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 12, y: 12 },
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: preloadPath,
    },
  });
  mainWindow = window;
  const emitFocus = (focused: boolean) => {
    if (window.isDestroyed()) return;
    if (process.platform === "darwin") window.setWindowButtonVisibility(focused);
    window.webContents.send("window:focus-changed", focused);
  };
  window.on("focus", () => emitFocus(true));
  window.on("blur", () => emitFocus(false));
  window.on("minimize", sendPetActivity);
  window.on("restore", sendPetActivity);
  window.webContents.on("did-finish-load", () => emitFocus(window.isFocused()));
  window.on("closed", () => {
    stopPreviewProcess();
    closePetWindow();
    mainWindow = undefined;
    app.quit();
  });
  window.webContents.on("render-process-gone", stopPreviewProcess);
  window.webContents.on("will-navigate", stopPreviewProcess);

  if (developmentServerUrl) {
    void window.loadURL(developmentServerUrl);
    return;
  }

  void window.loadFile(path.join(currentDirectory, "../dist/index.html"));
}

function startBackend() {
  if (isDevelopment) return Promise.resolve();
  const binary = path.join(process.resourcesPath, "backend", "sherpa-backend");
  const child = spawn(binary, [], {
    env: {
      ...process.env,
      SHERPA_PACKAGED: "1",
      SHERPA_RESOURCE_ROOT: process.resourcesPath,
      SHERPA_TOOL_RELAY_URL: "https://sherpa-relay-zjani637rq-bq.a.run.app",
      SHERPA_AGENT_API_URL: "https://sherpa-relay-zjani637rq-bq.a.run.app",
      SHERPA_AGENT_ENGINE_RESOURCE: "projects/sherpa-20260813/locations/europe-west1/reasoningEngines/8714245376636354560",
      SHERPA_AGENT_ENGINE_LOCATION: "europe-west1",
      SHERPA_MODEL_LOCATION: "global",
    },
  });
  backendProcess = child;
  return new Promise<void>((resolve, reject) => {
    let output = "";
    let settled = false;
    const readyTimer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error("Sherpa's local service did not start."));
    }, 60_000);
    const finish = (callback: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(readyTimer);
      callback();
    };
    child.stdout.on("data", (chunk: Buffer) => {
      output += chunk.toString();
      if (output.includes("SHERPA_BACKEND_READY")) finish(resolve);
      if (output.length > 8_192) output = output.slice(-4_096);
    });
    child.stderr.on("data", (chunk: Buffer) => {
      console.error(chunk.toString().trim());
    });
    child.on("error", (error) => finish(() => reject(error)));
    child.on("exit", (code) => {
      if (backendStopTimer) clearTimeout(backendStopTimer);
      backendStopTimer = undefined;
      if (backendProcess === child) backendProcess = undefined;
      finish(() => reject(new Error(`Sherpa's local service stopped (${code ?? "unknown"}).`)));
    });
  });
}

function stopBackend() {
  const child = backendProcess;
  backendProcess = undefined;
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  child.kill("SIGTERM");
  backendStopTimer = setTimeout(() => {
    if (child.exitCode === null && child.signalCode === null) child.kill("SIGKILL");
  }, 2_000);
}

function desktopBounds() {
  const displays = screen.getAllDisplays();
  const left = Math.min(...displays.map((display) => display.bounds.x));
  const top = Math.min(...displays.map((display) => display.bounds.y));
  const right = Math.max(...displays.map((display) => display.bounds.x + display.bounds.width));
  const bottom = Math.max(...displays.map((display) => display.bounds.y + display.bounds.height));
  return { x: left, y: top, width: right - left, height: bottom - top };
}

function createOverlayWindow(displayId: number, bounds: Electron.Rectangle) {
  const window = new BrowserWindow({
    ...bounds,
    transparent: true,
    frame: false,
    focusable: false,
    hasShadow: false,
    resizable: false,
    movable: false,
    skipTaskbar: true,
    show: false,
    backgroundColor: "#00000000",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: preloadPath,
    },
  });
  overlayWindows.set(displayId, window);
  window.setAlwaysOnTop(true, "screen-saver");
  window.setIgnoreMouseEvents(true, { forward: true });
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  window.on("closed", () => {
    if (overlayWindows.get(displayId) === window) overlayWindows.delete(displayId);
    readyOverlayDisplays.delete(displayId);
    pendingOverlays.delete(displayId);
  });
  window.webContents.on("did-fail-load", (_, code, description) => {
    console.error("Sherpa overlay failed to load", { displayId, code, description });
  });
  window.webContents.on("render-process-gone", (_, details) => {
    console.error("Sherpa overlay renderer stopped", { displayId, reason: details.reason });
  });

  if (developmentServerUrl) {
    void window.loadURL(`${developmentServerUrl}/overlay.html`);
  } else {
    void window.loadFile(path.join(currentDirectory, "../dist/overlay.html"));
  }
}

function syncOverlayWindows() {
  const displays = screen.getAllDisplays();
  const displayIds = new Set(displays.map((display) => display.id));
  for (const [displayId, window] of overlayWindows) {
    if (displayIds.has(displayId)) continue;
    overlayWindows.delete(displayId);
    readyOverlayDisplays.delete(displayId);
    pendingOverlays.delete(displayId);
    if (!window.isDestroyed()) window.destroy();
  }
  for (const display of displays) {
    const existing = overlayWindows.get(display.id);
    if (existing && !existing.isDestroyed()) {
      existing.setBounds(display.bounds);
    } else {
      createOverlayWindow(display.id, display.bounds);
    }
  }
}

function createPetWindow() {
  if (petWindow && !petWindow.isDestroyed()) return petWindow;
  const { workArea } = screen.getDisplayNearestPoint(screen.getCursorScreenPoint());
  const window = new BrowserWindow({
    width: PET_WIDTH,
    height: PET_HEIGHT,
    x: workArea.x + workArea.width - PET_WIDTH - 20,
    y: workArea.y + workArea.height - PET_HEIGHT - 10,
    transparent: true,
    frame: false,
    focusable: false,
    hasShadow: false,
    resizable: false,
    movable: false,
    skipTaskbar: true,
    show: false,
    backgroundColor: "#00000000",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: preloadPath,
    },
  });
  petWindow = window;
  window.setAlwaysOnTop(true, "floating");
  window.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  window.setFullScreenable(false);
  window.webContents.on("did-finish-load", () => {
    window.showInactive();
    sendPetActivity();
  });
  window.on("closed", () => {
    if (petWindow === window) petWindow = undefined;
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send("pet:state", false);
  });
  window.webContents.on("did-fail-load", (_, code, description) => {
    console.error("Sherpa pet failed to load", { code, description });
  });
  if (developmentServerUrl) void window.loadURL(`${developmentServerUrl}/pet.html`);
  else void window.loadFile(path.join(currentDirectory, "../dist/pet.html"));
  return window;
}

function sendPetActivity() {
  if (!petWindow || petWindow.isDestroyed()) return;
  petWindow.webContents.send("pet:activity", petActivity());
}

function petActivity() {
  return {
    working: petWorking,
    minimized: Boolean(mainWindow?.isMinimized()),
    transcript: petTranscript,
  };
}

function closePetWindow() {
  if (petWindow && !petWindow.isDestroyed()) petWindow.close();
}

function clampPetPosition(x: number, y: number) {
  const current = petWindow?.getBounds() || { x, y, width: PET_WIDTH, height: PET_HEIGHT };
  const { workArea } = screen.getDisplayMatching({ ...current, x, y });
  return {
    x: Math.max(workArea.x, Math.min(workArea.x + workArea.width - current.width, Math.round(x))),
    y: Math.max(workArea.y, Math.min(workArea.y + workArea.height - current.height, Math.round(y))),
  };
}

function overlayPoint(args: Record<string, unknown>) {
  const overlayX = typeof args.overlay_x === "number" ? args.overlay_x : undefined;
  const overlayY = typeof args.overlay_y === "number" ? args.overlay_y : undefined;
  if (overlayX !== undefined && overlayY !== undefined) {
    lastOverlayPoint = { x: overlayX, y: overlayY };
    return lastOverlayPoint;
  }
  const numericX = typeof args.x === "number" ? args.x : undefined;
  const numericY = typeof args.y === "number" ? args.y : undefined;
  if (numericX !== undefined && numericY !== undefined) {
    lastOverlayPoint = { x: numericX, y: numericY };
    return lastOverlayPoint;
  }

  const at = args.at;
  const hasWindowTarget = Boolean(args.app || args.pid || args.window_id || args.window_title);
  if (typeof at === "string" && (!hasWindowTarget || args.global === true)) {
    const [x, y] = at.split(",").map(Number);
    if (Number.isFinite(x) && Number.isFinite(y)) {
      lastOverlayPoint = { x, y };
      return lastOverlayPoint;
    }
  }
  if (lastOverlayPoint) return lastOverlayPoint;
  const windowBounds = mainWindow?.getBounds();
  const bounds = desktopBounds();
  lastOverlayPoint = windowBounds
    ? { x: windowBounds.x + 22, y: windowBounds.y + 274 }
    : { x: bounds.x + 40, y: bounds.y + 120 };
  return lastOverlayPoint;
}

function configureOverlayEvents() {
  const showOverlay = (payload: OverlayPayload) => {
    const point = overlayPoint(payload.args);
    const display = screen.getDisplayNearestPoint({ x: Math.round(point.x), y: Math.round(point.y) });
    const target = overlayWindows.get(display.id);
    for (const [displayId, window] of overlayWindows) {
      if (displayId !== display.id && !window.isDestroyed()) window.hide();
      if (displayId !== display.id) pendingOverlays.delete(displayId);
    }
    if (!target || target.isDestroyed() || !readyOverlayDisplays.has(display.id)) {
      pendingOverlays.set(display.id, payload);
      return;
    }
    if (!target.isVisible()) {
      target.showInactive();
    }
    const bounds = target.getBounds();
    const x = point.x - bounds.x;
    const y = point.y - bounds.y;
    if (payload.action.endsWith("_click")) {
      console.info("Sherpa overlay click", { x: point.x, y: point.y });
    }
    target.webContents.send("overlay:update", {
      ...payload,
      x,
      y,
      horizontal: x > bounds.width - 300 ? "left" : "right",
      vertical: y > bounds.height - 110 ? "up" : "down",
    });
  };
  const hideOverlay = (id: string) => {
    pendingOverlays.clear();
    for (const [displayId, target] of overlayWindows) {
      if (target.isDestroyed() || !readyOverlayDisplays.has(displayId)) continue;
      target.webContents.send("overlay:hide", id);
      target.hide();
    }
  };

  ipcMain.on("overlay:ready", (event) => {
    const entry = [...overlayWindows.entries()].find(([, window]) => event.sender === window.webContents);
    if (!entry) return;
    const [displayId, window] = entry;
    readyOverlayDisplays.add(displayId);
    const payload = pendingOverlays.get(displayId);
    if (payload) {
      pendingOverlays.delete(displayId);
      showOverlay(payload);
    } else {
      window.hide();
    }
  });
  ipcMain.on("overlay:show", (event, payload: OverlayPayload) => {
    if (event.sender !== mainWindow?.webContents) return;
    showOverlay(payload);
  });
  ipcMain.on("overlay:hide", (event, id: string) => {
    if (event.sender !== mainWindow?.webContents) return;
    hideOverlay(id);
  });
}

function configureSystemEvents() {
  ipcMain.on("voice:debug", (event, payload: Record<string, unknown>) => {
    if (event.sender !== mainWindow?.webContents || !payload) return;
    console.info("voice.playback", payload);
  });
  ipcMain.removeHandler("system:open-external");
  ipcMain.handle("system:open-external", async (event, url: string) => {
    if (event.sender !== mainWindow?.webContents) return false;
    const target = new URL(url);
    if (target.protocol !== "https:") return false;
    await shell.openExternal(target.toString());
    return true;
  });
}

function configurePhotoEvents() {
  ipcMain.removeHandler("photo:save");
  ipcMain.handle("photo:save", async (event, bytes: Uint8Array) => {
    if (event.sender !== mainWindow?.webContents || !bytes?.byteLength) {
      throw new Error("The captured photo was empty.");
    }
    const directory = path.join(app.getPath("pictures"), "Sherpa Captures");
    await mkdir(directory, { recursive: true });
    const timestamp = new Date().toISOString().replaceAll(":", "-").replace(".", "-");
    const photoPath = path.join(directory, `Sherpa-${timestamp}.jpg`);
    await writeFile(photoPath, Buffer.from(bytes));
    return photoPath;
  });
}

function configurePetEvents() {
  ipcMain.handle("pet:wake", (event) => {
    if (event.sender !== mainWindow?.webContents) return false;
    createPetWindow();
    mainWindow.webContents.send("pet:state", true);
    return true;
  });
  ipcMain.on("pet:sleep", (event) => {
    if (event.sender === mainWindow?.webContents) closePetWindow();
  });
  ipcMain.on("pet:working", (event, working: boolean) => {
    if (event.sender !== mainWindow?.webContents || typeof working !== "boolean") return;
    petWorking = working;
    sendPetActivity();
  });
  ipcMain.on("pet:transcript", (event, transcript: PetTranscriptPayload) => {
    if (event.sender !== mainWindow?.webContents || !transcript || !Array.isArray(transcript.entries)) return;
    petTranscript = transcript;
    sendPetActivity();
  });
  ipcMain.on("pet:close", (event) => {
    if (event.sender === petWindow?.webContents) closePetWindow();
  });
  ipcMain.on("pet:voice-toggle", (event) => {
    if (event.sender === petWindow?.webContents && mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("pet:voice-toggle");
    }
  });
  ipcMain.on("pet:celebrate", (event, count: number) => {
    if (event.sender === mainWindow?.webContents && petWindow && !petWindow.isDestroyed()) {
      petWindow.webContents.send("pet:celebrate", Number.isInteger(count) && count > 0 ? count : 1);
    }
  });
  ipcMain.handle("pet:activity", (event) => {
    if (event.sender !== petWindow?.webContents) return { working: false };
    return petActivity();
  });
  ipcMain.handle("pet:state", (event) => {
    if (event.sender !== mainWindow?.webContents) return false;
    return Boolean(petWindow && !petWindow.isDestroyed());
  });
  ipcMain.handle("pet:bounds", (event) => {
    if (event.sender !== petWindow?.webContents) return null;
    return petWindow.getBounds();
  });
  ipcMain.on("pet:drag", (event, x: number, y: number) => {
    if (event.sender !== petWindow?.webContents || !Number.isFinite(x) || !Number.isFinite(y)) return;
    const next = clampPetPosition(x, y);
    petWindow.setPosition(next.x, next.y, false);
  });
}

function configurePreviewEvents() {
  ipcMain.handle("preview:start", (event, taskId: string, target: PreviewTarget) => {
    if (event.sender !== mainWindow?.webContents || !taskId || !validPreviewTarget(target)) return false;
    const targetKey = previewTargetKey(target);
    if (previewTaskId === taskId && previewTarget === targetKey && previewProcess) return true;
    if (previewStopping) {
      pendingPreview = { taskId, target, targetKey };
      return true;
    }
    const child = ensurePreviewProcess();
    console.info("preview.target_switching", {
      taskId,
      from: previewTarget,
      to: targetKey,
      pid: child.pid,
    });
    previewTaskId = taskId;
    previewTarget = targetKey;
    child.stdin.write(`${JSON.stringify({ action: "switch", task_id: taskId, target })}\n`);
    return true;
  });
  ipcMain.on("preview:stop", (event, taskId: string) => {
    if (event.sender === mainWindow?.webContents && previewTaskId === taskId) idlePreview();
  });
  ipcMain.on("preview:stop-all", (event) => {
    if (event.sender === mainWindow?.webContents) stopPreviewProcess();
  });
}

function ensurePreviewProcess() {
  if (previewProcess && !previewStopping) return previewProcess;
  const binary = !isDevelopment
    ? path.join(process.resourcesPath, "window-capture")
    : path.join(app.getAppPath(), "dist-native/window-capture");
  const child = spawn(binary);
  previewProcess = child;
  previewStopping = false;
  previewBuffer = Buffer.alloc(0);
  console.info("preview.broker_started", { pid: child.pid });
  child.stdout.on("data", (chunk: Buffer) => {
    previewBuffer = Buffer.concat([previewBuffer, chunk]);
    while (previewBuffer.length >= 4) {
      const length = previewBuffer.readUInt32BE(0);
      if (previewBuffer.length < length + 4) break;
      const frame = previewBuffer.subarray(4, length + 4);
      previewBuffer = previewBuffer.subarray(length + 4);
      if (frame[0] === 0x7b) {
        try {
          const payload = JSON.parse(frame.toString()) as {
            type: string;
            task_id?: string;
            x?: number;
            y?: number;
            width?: number;
            height?: number;
            message?: string;
          };
          if (payload.type === "metadata" && payload.task_id) {
            mainWindow?.webContents.send("preview:metadata", payload.task_id, payload);
            console.info("preview.target_active", { taskId: payload.task_id, pid: child.pid });
          } else if (payload.type === "stopped") {
            console.info("preview.capture_stopped", { pid: child.pid });
          } else if ((payload.type === "command_error" || payload.type === "stream_error") && previewTaskId) {
            mainWindow?.webContents.send("preview:error", previewTaskId, String(payload.message || "Window preview stopped."));
            if (payload.type === "stream_error") stopPreviewProcess();
          }
        } catch {
          if (previewTaskId) mainWindow?.webContents.send("preview:error", previewTaskId, "Window preview metadata was invalid.");
        }
      } else if (frame[0] === 0 && frame.length >= 3) {
        const taskLength = frame.readUInt16BE(1);
        if (frame.length < taskLength + 3) continue;
        const taskId = frame.subarray(3, taskLength + 3).toString();
        const image = frame.subarray(taskLength + 3);
        mainWindow?.webContents.send("preview:frame", taskId, Uint8Array.from(image));
      }
    }
  });
  let errorText = "";
  child.stderr.on("data", (chunk: Buffer) => { errorText += chunk.toString(); });
  child.on("error", (error) => {
    if (previewTaskId) mainWindow?.webContents.send("preview:error", previewTaskId, error.message);
  });
  child.on("exit", (code) => {
    clearPreviewExitTimers();
    const taskId = previewTaskId;
    const expected = previewStopping;
    if (previewProcess === child) previewProcess = undefined;
    previewStopping = false;
    previewTaskId = undefined;
    previewTarget = undefined;
    previewBuffer = Buffer.alloc(0);
    console.info("preview.broker_exited", { pid: child.pid, code, expected });
    if (!expected && taskId) mainWindow?.webContents.send(
      "preview:error",
      taskId,
      errorText.trim() || "Window preview stopped.",
    );
    const pending = pendingPreview;
    pendingPreview = undefined;
    if (pending && mainWindow && !mainWindow.isDestroyed()) {
      const next = ensurePreviewProcess();
      previewTaskId = pending.taskId;
      previewTarget = pending.targetKey;
      next.stdin.write(`${JSON.stringify({ action: "switch", task_id: pending.taskId, target: pending.target })}\n`);
    }
  });
  return child;
}

function validPreviewTarget(target: PreviewTarget) {
  return Boolean(
    target
    && (target.app || target.pid)
    && target.app !== "frontmost"
    && !target.app?.includes(":"),
  );
}

function previewTargetKey(target: PreviewTarget) {
  return [target.app, target.pid, target.window_id, target.window_title]
    .map((value) => value ?? "")
    .join(":");
}

function idlePreview() {
  const child = previewProcess;
  previewTaskId = undefined;
  previewTarget = undefined;
  if (child && !previewStopping) child.stdin.write(`${JSON.stringify({ action: "idle" })}\n`);
}

function stopPreviewProcess() {
  const child = previewProcess;
  previewTaskId = undefined;
  previewTarget = undefined;
  pendingPreview = undefined;
  if (!child || previewStopping) return;
  previewStopping = true;
  console.info("preview.broker_stopping", { pid: child.pid });
  child.stdin.end(`${JSON.stringify({ action: "stop" })}\n`);
  previewTerminateTimer = setTimeout(() => {
    if (child.exitCode === null && child.signalCode === null) {
      console.warn("preview.broker_terminating", { pid: child.pid });
      child.kill("SIGTERM");
    }
  }, 750);
  previewKillTimer = setTimeout(() => {
    if (child.exitCode === null && child.signalCode === null) {
      console.error("preview.broker_killing", { pid: child.pid });
      child.kill("SIGKILL");
    }
  }, 1500);
}

function clearPreviewExitTimers() {
  if (previewTerminateTimer) clearTimeout(previewTerminateTimer);
  if (previewKillTimer) clearTimeout(previewKillTimer);
  previewTerminateTimer = undefined;
  previewKillTimer = undefined;
}

app.whenReady().then(async () => {
  app.setName("Sherpa");
  const dock = app.dock;
  if (process.platform === "darwin" && dock) {
    dock.show();
    dock.setIcon(dockIconPath);
  }
  try {
    await startBackend();
  } catch (error) {
    dialog.showErrorBox(
      "Sherpa could not start",
      error instanceof Error ? error.message : "The local service could not start.",
    );
    app.quit();
    return;
  }
  configureSystemEvents();
  configurePhotoEvents();
  configurePetEvents();
  configurePreviewEvents();
  createWindow();
  configureOverlayEvents();
  syncOverlayWindows();

  screen.on("display-added", syncOverlayWindows);
  screen.on("display-removed", syncOverlayWindows);
  screen.on("display-metrics-changed", syncOverlayWindows);

  app.on("activate", () => {
    if (!mainWindow) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  stopPreviewProcess();
  app.quit();
});

app.on("before-quit", stopPreviewProcess);
app.on("before-quit", closePetWindow);
app.on("before-quit", stopBackend);
