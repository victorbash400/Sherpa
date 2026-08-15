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
  app?: string;
  pid?: number;
  window_id?: number;
  window_title?: string;
};

declare global {
  interface Window {
    sherpaOverlay?: {
      ready: () => void;
      dock: () => void;
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
      onFrame: (callback: (taskId: string, frame: string) => void) => () => void;
      onError: (callback: (taskId: string, message: string) => void) => () => void;
    };
  }
}
