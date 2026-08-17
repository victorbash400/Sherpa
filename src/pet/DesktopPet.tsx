import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import { PetCloseButton } from "./PetCloseButton";
import { PetTranscriptBubble } from "./PetTranscriptBubble";
import { PetVoiceButton } from "./PetVoiceButton";
import type { PetActivity } from "../types/sherpaOverlay";
import "./DesktopPet.css";

const frameDirectory = "monster_desktop_pet_sprite_bundle/frames_png/";
const idleFrames = [
  "frame_10_idle_subtle_breathing_rise.png",
  "frame_11_idle_blink_beginning.png",
  "frame_12_idle_eyes_closed_blink.png",
  "frame_14_idle_return_to_neutral.png",
];
const idleFrameDurations = [2400, 140, 120, 1400];
const workingFrames = [
  "frame_19_working_begin_action.png",
  "frame_20_working_first_tap.png",
  "frame_21_working_alternate_tap.png",
  "frame_22_working_return_loop.png",
];
const successUpFrame = "frame_27_success_realizes_success.png";
const successDownFrame = "frame_28_success_compact_celebration.png";
const successSettleFrame = "frame_29_success_satisfied_settle.png";
const successFrames = [
  successUpFrame,
  successDownFrame,
  successUpFrame,
  successDownFrame,
  successUpFrame,
  successDownFrame,
  successSettleFrame,
];
const successFrameDurations = [360, 360, 360, 360, 360, 360, 700];

function frameSource(name: string) {
  return new URL(`${frameDirectory}${name}`, document.baseURI).toString();
}

const frameOffsets: Record<string, { x: number; y: number }> = {
  [idleFrames[0]]: { x: 0, y: 0 },
  [idleFrames[1]]: { x: 8, y: 0 },
  [idleFrames[2]]: { x: 16, y: -1 },
  [idleFrames[3]]: { x: 1, y: 8 },
  [workingFrames[0]]: { x: -1, y: -14 },
  [workingFrames[1]]: { x: -3, y: -14 },
  [workingFrames[2]]: { x: -8, y: -12 },
  [workingFrames[3]]: { x: -2, y: -12 },
  [successUpFrame]: { x: -10, y: -4 },
  [successDownFrame]: { x: 7, y: -5 },
  [successSettleFrame]: { x: -3, y: 7 },
};

export function DesktopPet() {
  const [frame, setFrame] = useState(idleFrames[0]);
  const [celebrating, setCelebrating] = useState(false);
  const [activity, setActivity] = useState<PetActivity>({
    working: false,
    minimized: false,
    transcript: { entries: [], hue: 0, status: "idle" },
  });
  const draggingRef = useRef<{ x: number; y: number } | undefined>(undefined);
  const pointerDownRef = useRef(false);
  const celebrationQueueRef = useRef(0);

  const queueCelebration = (count = 1) => {
    celebrationQueueRef.current += count;
    setCelebrating(true);
  };

  useEffect(() => {
    const applyActivity = (nextActivity: PetActivity) => setActivity(nextActivity);
    const removeListener = window.sherpaPet?.onActivityChanged(applyActivity);
    void window.sherpaPet?.activity().then(applyActivity);
    return removeListener;
  }, []);

  useEffect(() => window.sherpaPet?.onCelebrate((count) => {
    queueCelebration(count);
  }), []);

  useEffect(() => {
    let animation = 0;
    let lastFrame = performance.now();
    let frameIndex = 0;
    const initialFrames = celebrating ? successFrames : activity.working ? workingFrames : idleFrames;
    setFrame(initialFrames[0]);

    const animate = (now: number) => {
      const frames = celebrating ? successFrames : activity.working ? workingFrames : idleFrames;
      const frameDuration = celebrating
        ? successFrameDurations[frameIndex]
        : activity.working
          ? 300
          : idleFrameDurations[frameIndex];
      if (now - lastFrame >= frameDuration) {
        if (celebrating && frameIndex === frames.length - 1) {
          celebrationQueueRef.current = Math.max(0, celebrationQueueRef.current - 1);
          if (celebrationQueueRef.current > 0) {
            frameIndex = 0;
            setFrame(frames[0]);
            lastFrame = now;
            animation = requestAnimationFrame(animate);
            return;
          }
          setCelebrating(false);
          return;
        }
        frameIndex = (frameIndex + 1) % frames.length;
        setFrame(frames[frameIndex]);
        lastFrame = now;
      }
      animation = requestAnimationFrame(animate);
    };
    animation = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animation);
  }, [activity.working, celebrating]);

  useEffect(() => {
    const stopDrag = () => {
      pointerDownRef.current = false;
      draggingRef.current = undefined;
    };
    window.addEventListener("pointerup", stopDrag);
    window.addEventListener("pointercancel", stopDrag);
    window.addEventListener("blur", stopDrag);
    return () => {
      window.removeEventListener("pointerup", stopDrag);
      window.removeEventListener("pointercancel", stopDrag);
      window.removeEventListener("blur", stopDrag);
    };
  }, []);

  const startDrag = async (event: ReactPointerEvent<HTMLImageElement>) => {
    if (event.button !== 0) return;
    pointerDownRef.current = true;
    event.currentTarget.setPointerCapture(event.pointerId);
    const bounds = await window.sherpaPet?.bounds();
    if (!bounds || !pointerDownRef.current) return;
    draggingRef.current = { x: event.screenX - bounds.x, y: event.screenY - bounds.y };
  };
  const drag = (event: ReactPointerEvent<HTMLImageElement>) => {
    if ((event.buttons & 1) === 0) {
      pointerDownRef.current = false;
      draggingRef.current = undefined;
      return;
    }
    const offset = draggingRef.current;
    if (offset) window.sherpaPet?.drag(event.screenX - offset.x, event.screenY - offset.y);
  };
  const stopDrag = () => {
    pointerDownRef.current = false;
    draggingRef.current = undefined;
  };
  const voiceActive = ["connecting", "listening", "speaking"].includes(activity.transcript.status);
  const hasTranscript = activity.transcript.entries.some((entry) => entry.text.trim());
  const showTranscript = activity.minimized || voiceActive || hasTranscript;

  return (
    <main className="desktop-pet-shell">
      {showTranscript ? <PetTranscriptBubble transcript={activity.transcript} /> : null}
      <PetCloseButton onClose={() => window.sherpaPet?.close()} />
      <PetVoiceButton
        active={voiceActive}
        hue={activity.transcript.hue}
        onToggle={() => window.sherpaPet?.toggleVoice()}
      />
      <img
        className="desktop-pet"
        draggable={false}
        src={frameSource(frame)}
        style={{ translate: `${frameOffsets[frame]?.x ?? 0}px ${frameOffsets[frame]?.y ?? 0}px` }}
        alt=""
        onPointerCancel={stopDrag}
        onPointerDown={(event) => void startDrag(event)}
        onPointerMove={drag}
        onPointerUp={stopDrag}
      />
    </main>
  );
}
