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

export type PetActivity = {
  working: boolean;
  minimized: boolean;
  transcript: {
    entries: Array<{ id: string; role: "user" | "assistant"; text: string }>;
    hue: number;
    status: string;
  };
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
      debugVoice: (payload: Record<string, unknown>) => void;
      onWindowFocusChanged: (callback: (focused: boolean) => void) => () => void;
    };
    sherpaPhotos?: {
      save: (bytes: Uint8Array) => Promise<string>;
    };
    sherpaPreview?: {
      start: (taskId: string, target: PreviewTarget) => Promise<boolean>;
      stop: (taskId: string) => void;
      stopAll: () => void;
      onFrame: (callback: (taskId: string, frame: Uint8Array) => void) => () => void;
      onError: (callback: (taskId: string, message: string) => void) => () => void;
      onMetadata: (callback: (taskId: string, bounds: PreviewBounds) => void) => () => void;
    };
    sherpaPet?: {
      wake: () => Promise<boolean>;
      sleep: () => void;
      isAwake: () => Promise<boolean>;
      setWorking: (working: boolean) => void;
      setTranscript: (transcript: PetActivity["transcript"]) => void;
      activity: () => Promise<PetActivity>;
      close: () => void;
      toggleVoice: () => void;
      celebrate: (count?: number) => void;
      bounds: () => Promise<{ x: number; y: number; width: number; height: number } | null>;
      drag: (x: number, y: number) => void;
      onActivityChanged: (callback: (activity: PetActivity) => void) => () => void;
      onVoiceToggle: (callback: () => void) => () => void;
      onCelebrate: (callback: (count: number) => void) => () => void;
      onStateChanged: (callback: (awake: boolean) => void) => () => void;
    };
  }
}
