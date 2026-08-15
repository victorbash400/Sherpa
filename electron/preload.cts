const { contextBridge, ipcRenderer } = require("electron") as typeof import("electron");

contextBridge.exposeInMainWorld("sherpaOverlay", {
  ready: () => ipcRenderer.send("overlay:ready"),
  dock: () => ipcRenderer.send("overlay:dock"),
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
