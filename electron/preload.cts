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
});

contextBridge.exposeInMainWorld("sherpaPreview", {
  start: (taskId: string, target: unknown) => ipcRenderer.invoke("preview:start", taskId, target),
  stop: (taskId: string) => ipcRenderer.send("preview:stop", taskId),
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
