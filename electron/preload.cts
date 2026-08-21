const { contextBridge, ipcRenderer } = require("electron") as typeof import("electron");

contextBridge.exposeInMainWorld("sherpaOverlay", {
  ready: () => ipcRenderer.send("overlay:ready"),
  show: (payload: unknown) => ipcRenderer.send("overlay:show", payload),
  hide: (id: string) => ipcRenderer.send("overlay:hide", id),
  onUpdate: (callback: (payload: unknown) => void) => {
    const listener = (_: Electron.IpcRendererEvent, payload: unknown) => callback(payload);
    ipcRenderer.on("overlay:update", listener);
    return () => ipcRenderer.removeListener("overlay:update", listener);
  },
  onHide: (callback: (id: string) => void) => {
    const listener = (_: Electron.IpcRendererEvent, id: string) => callback(id);
    ipcRenderer.on("overlay:hide", listener);
    return () => ipcRenderer.removeListener("overlay:hide", listener);
  },
});

contextBridge.exposeInMainWorld("sherpaSystem", {
  openExternal: (url: string) => ipcRenderer.invoke("system:open-external", url),
  debugVoice: (payload: unknown) => ipcRenderer.send("voice:debug", payload),
  onWindowFocusChanged: (callback: (focused: boolean) => void) => {
    const listener = (_: Electron.IpcRendererEvent, focused: boolean) => callback(focused);
    ipcRenderer.on("window:focus-changed", listener);
    return () => ipcRenderer.removeListener("window:focus-changed", listener);
  },
});

contextBridge.exposeInMainWorld("sherpaPhotos", {
  save: (bytes: Uint8Array) => ipcRenderer.invoke("photo:save", bytes),
});

contextBridge.exposeInMainWorld("sherpaPreview", {
  start: (taskId: string, target: unknown) => ipcRenderer.invoke("preview:start", taskId, target),
  stop: (taskId: string) => ipcRenderer.send("preview:stop", taskId),
  stopAll: () => ipcRenderer.send("preview:stop-all"),
  onFrame: (callback: (taskId: string, frame: Uint8Array) => void) => {
    const listener = (_: Electron.IpcRendererEvent, taskId: string, frame: Uint8Array) => callback(taskId, frame);
    ipcRenderer.on("preview:frame", listener);
    return () => ipcRenderer.removeListener("preview:frame", listener);
  },
  onError: (callback: (taskId: string, message: string) => void) => {
    const listener = (_: Electron.IpcRendererEvent, taskId: string, message: string) => callback(taskId, message);
    ipcRenderer.on("preview:error", listener);
    return () => ipcRenderer.removeListener("preview:error", listener);
  },
  onMetadata: (callback: (taskId: string, bounds: unknown) => void) => {
    const listener = (_: Electron.IpcRendererEvent, taskId: string, bounds: unknown) => callback(taskId, bounds);
    ipcRenderer.on("preview:metadata", listener);
    return () => ipcRenderer.removeListener("preview:metadata", listener);
  },
});

contextBridge.exposeInMainWorld("sherpaPet", {
  wake: () => ipcRenderer.invoke("pet:wake"),
  sleep: () => ipcRenderer.send("pet:sleep"),
  isAwake: () => ipcRenderer.invoke("pet:state"),
  setWorking: (working: boolean) => ipcRenderer.send("pet:working", working),
  setTranscript: (transcript: unknown) => ipcRenderer.send("pet:transcript", transcript),
  activity: () => ipcRenderer.invoke("pet:activity"),
  close: () => ipcRenderer.send("pet:close"),
  toggleVoice: () => ipcRenderer.send("pet:voice-toggle"),
  celebrate: (count = 1) => ipcRenderer.send("pet:celebrate", count),
  bounds: () => ipcRenderer.invoke("pet:bounds"),
  drag: (x: number, y: number) => ipcRenderer.send("pet:drag", x, y),
  onActivityChanged: (callback: (activity: unknown) => void) => {
    const listener = (_: Electron.IpcRendererEvent, activity: unknown) => callback(activity);
    ipcRenderer.on("pet:activity", listener);
    return () => ipcRenderer.removeListener("pet:activity", listener);
  },
  onVoiceToggle: (callback: () => void) => {
    const listener = () => callback();
    ipcRenderer.on("pet:voice-toggle", listener);
    return () => ipcRenderer.removeListener("pet:voice-toggle", listener);
  },
  onCelebrate: (callback: (count: number) => void) => {
    const listener = (_: Electron.IpcRendererEvent, count: number) => callback(count);
    ipcRenderer.on("pet:celebrate", listener);
    return () => ipcRenderer.removeListener("pet:celebrate", listener);
  },
  onStateChanged: (callback: (awake: boolean) => void) => {
    const listener = (_: Electron.IpcRendererEvent, awake: boolean) => callback(awake);
    ipcRenderer.on("pet:state", listener);
    return () => ipcRenderer.removeListener("pet:state", listener);
  },
});
