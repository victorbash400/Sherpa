export {};

export type OverlayAction = {
  id: string;
  action: string;
  message: string;
  intent?: string;
  args: Record<string, unknown>;
};

export type OverlayUpdate = OverlayAction & {
  x: number;
  y: number;
  horizontal: "left" | "right";
  vertical: "up" | "down";
};

export type PreviewTarget = {
  kind?: "window" | "workspace";
  app?: string;
  mime_type?: string;
  pid?: number;
  resource_id?: string;
  revision?: string;
  title?: string;
  window_id?: number;
  window_title?: string;
};

export type PreviewBounds = {
  type: "metadata";
  x: number;
  y: number;
  width: number;
  height: number;
};

export type PreviewCursor = {
  id: string;
  action: string;
  x: number;
  y: number;
};

declare global {
  interface Window {
    sherpaOverlay?: {
      ready: () => void;
      show: (payload: OverlayAction) => void;
      hide: (id: string) => void;
      onUpdate: (callback: (payload: OverlayUpdate) => void) => () => void;
      onHide: (callback: (id: string) => void) => () => void;
    };
    sherpaSystem?: {
      openExternal: (url: string) => Promise<boolean>;
    };
    sherpaPreview?: {
      start: (taskId: string, target: PreviewTarget) => Promise<boolean>;
      stop: (taskId: string) => void;
      stopAll: () => void;
      onFrame: (callback: (taskId: string, frame: Uint8Array) => void) => () => void;
      onError: (callback: (taskId: string, message: string) => void) => () => void;
      onMetadata: (callback: (taskId: string, bounds: PreviewBounds) => void) => () => void;
    };
  }
}
