import { app, BrowserWindow, ipcMain, screen, shell } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const preloadPath = path.join(currentDirectory, "preload.cjs");
const dockIconPath = app.isPackaged
  ? path.join(currentDirectory, "../dist/sherpa-dock-icon.png")
  : path.join(app.getAppPath(), "public/sherpa-dock-icon.png");
let mainWindow: BrowserWindow | undefined;
let overlayWindow: BrowserWindow | undefined;
let overlayReady = false;
let pendingOverlay: OverlayPayload | undefined;
let lastOverlayPoint: { x: number; y: number } | undefined;
let dockTimer: NodeJS.Timeout | undefined;

type OverlayPayload = {
  id: string;
  action: string;
  message: string;
  intent?: string;
  args: Record<string, unknown>;
};

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
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: preloadPath,
    },
  });
  mainWindow = window;
  window.on("closed", () => {
    mainWindow = undefined;
    if (process.platform !== "darwin") app.quit();
  });

  if (!app.isPackaged) {
    void window.loadURL("http://localhost:5173");
    return;
  }

  void window.loadFile(path.join(currentDirectory, "../dist/index.html"));
}

function desktopBounds() {
  const displays = screen.getAllDisplays();
  const left = Math.min(...displays.map((display) => display.bounds.x));
  const top = Math.min(...displays.map((display) => display.bounds.y));
  const right = Math.max(...displays.map((display) => display.bounds.x + display.bounds.width));
  const bottom = Math.max(...displays.map((display) => display.bounds.y + display.bounds.height));
  return { x: left, y: top, width: right - left, height: bottom - top };
}

function createOverlayWindow() {
  const bounds = desktopBounds();
  overlayReady = false;
  overlayWindow = new BrowserWindow({
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
  overlayWindow.setAlwaysOnTop(true, "screen-saver");
  overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  overlayWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  overlayWindow.on("closed", () => {
    overlayWindow = undefined;
    overlayReady = false;
  });
  overlayWindow.webContents.on("did-fail-load", (_, code, description) => {
    console.error("Sherpa overlay failed to load", { code, description });
  });
  overlayWindow.webContents.on("render-process-gone", (_, details) => {
    console.error("Sherpa overlay renderer stopped", { reason: details.reason });
  });

  if (!app.isPackaged) {
    void overlayWindow.loadURL("http://localhost:5173/overlay.html");
  } else {
    void overlayWindow.loadFile(path.join(currentDirectory, "../dist/overlay.html"));
  }
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

function dockPoint() {
  const windowBounds = mainWindow?.getBounds();
  const bounds = desktopBounds();
  return windowBounds
    ? { x: windowBounds.x + 21, y: windowBounds.y + 274 }
    : { x: bounds.x + 40, y: bounds.y + 120 };
}

function configureOverlayEvents() {
  const showOverlay = (payload: OverlayPayload) => {
    const target = overlayWindow;
    if (!target || target.isDestroyed() || !overlayReady) {
      pendingOverlay = payload;
      return;
    }
    if (dockTimer) clearTimeout(dockTimer);
    dockTimer = undefined;
    if (!target.isVisible()) {
      lastOverlayPoint = dockPoint();
      target.showInactive();
    }
    const bounds = target.getBounds();
    const point = overlayPoint(payload.args);
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
  const dockOverlay = () => {
    const point = dockPoint();
    showOverlay({
      id: "sherpa-docked",
      action: "docked",
      message: "",
      args: { overlay_x: point.x, overlay_y: point.y },
    });
    dockTimer = setTimeout(() => {
      overlayWindow?.hide();
      dockTimer = undefined;
    }, 720);
  };

  ipcMain.on("overlay:ready", (event) => {
    if (event.sender !== overlayWindow?.webContents) return;
    overlayReady = true;
    if (pendingOverlay) {
      const payload = pendingOverlay;
      pendingOverlay = undefined;
      showOverlay(payload);
    } else {
      overlayWindow.hide();
    }
  });
  ipcMain.on("overlay:dock", (event) => {
    if (event.sender !== mainWindow?.webContents) return;
    pendingOverlay = undefined;
    dockOverlay();
  });
  ipcMain.on("overlay:show", (event, payload: OverlayPayload) => {
    if (event.sender !== mainWindow?.webContents) return;
    showOverlay(payload);
  });
  ipcMain.on("overlay:hide", (event, id: string) => {
    if (event.sender !== mainWindow?.webContents) return;
    if (pendingOverlay?.id === id) pendingOverlay = undefined;
    if (!overlayReady) return;
    dockOverlay();
  });
}

function configureSystemEvents() {
  ipcMain.removeHandler("system:open-external");
  ipcMain.handle("system:open-external", async (event, url: string) => {
    if (event.sender !== mainWindow?.webContents) return false;
    const target = new URL(url);
    if (target.protocol !== "https:") return false;
    await shell.openExternal(target.toString());
    return true;
  });
}

app.whenReady().then(() => {
  app.setName("Sherpa");
  const dock = app.dock;
  if (process.platform === "darwin" && dock) {
    dock.show();
    dock.setIcon(dockIconPath);
  }
  configureSystemEvents();
  createWindow();
  createOverlayWindow();
  configureOverlayEvents();

  screen.on("display-added", () => overlayWindow?.setBounds(desktopBounds()));
  screen.on("display-removed", () => overlayWindow?.setBounds(desktopBounds()));
  screen.on("display-metrics-changed", () => overlayWindow?.setBounds(desktopBounds()));

  app.on("activate", () => {
    if (!mainWindow) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
