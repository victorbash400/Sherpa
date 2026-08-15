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
  }
}
