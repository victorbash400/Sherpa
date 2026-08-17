import { useEffect, useRef, useState } from "react";
import { Camera } from "lucide-react";
import "./CameraOrbPreview.css";

interface CameraOrbPreviewProps {
  active: boolean;
  onFrame: (data: string, mimeType: string) => void;
  onError: (message?: string) => void;
}

type VideoWithFrameCallbacks = HTMLVideoElement & {
  requestVideoFrameCallback: (callback: (now: number) => void) => number;
  cancelVideoFrameCallback: (handle: number) => void;
};

export function CameraOrbPreview({ active, onError, onFrame }: CameraOrbPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const frameCallbackRef = useRef<number | undefined>(undefined);
  const encodingRef = useRef(false);
  const lastFrameAtRef = useRef(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!active) {
      setReady(false);
      onError(undefined);
      return;
    }
    let disposed = false;
    let stream: MediaStream | undefined;
    const video = videoRef.current as VideoWithFrameCallbacks | null;
    if (!video) return;

    const captureFrame = (now: number) => {
      if (disposed) return;
      frameCallbackRef.current = video.requestVideoFrameCallback(captureFrame);
      if (!video.videoWidth || now - lastFrameAtRef.current < 1000 || encodingRef.current) return;
      lastFrameAtRef.current = now;
      encodingRef.current = true;
      const canvas = document.createElement("canvas");
      const scale = Math.min(1, 640 / video.videoWidth);
      canvas.width = Math.round(video.videoWidth * scale);
      canvas.height = Math.round(video.videoHeight * scale);
      const context = canvas.getContext("2d");
      if (!context) {
        encodingRef.current = false;
        return;
      }
      context.translate(canvas.width, 0);
      context.scale(-1, 1);
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (!blob || disposed) {
          encodingRef.current = false;
          return;
        }
        const reader = new FileReader();
        reader.addEventListener("load", () => {
          const result = String(reader.result || "");
          onFrame(result.slice(result.indexOf(",") + 1), blob.type);
          encodingRef.current = false;
        }, { once: true });
        reader.readAsDataURL(blob);
      }, "image/jpeg", 0.72);
    };

    void navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 960 } } })
      .then(async (nextStream) => {
        if (disposed) {
          nextStream.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = nextStream;
        video.srcObject = stream;
        await video.play();
        setReady(true);
        onError(undefined);
        frameCallbackRef.current = video.requestVideoFrameCallback(captureFrame);
      })
      .catch((reason: unknown) => {
        setReady(false);
        onError(reason instanceof Error ? reason.message : "Camera could not start.");
      });

    return () => {
      disposed = true;
      if (frameCallbackRef.current !== undefined) video.cancelVideoFrameCallback(frameCallbackRef.current);
      frameCallbackRef.current = undefined;
      video.srcObject = null;
      stream?.getTracks().forEach((track) => track.stop());
      setReady(false);
    };
  }, [active, onError, onFrame]);

  return (
    <div className="camera-orb-preview" data-ready={ready} aria-hidden={!active}>
      <video ref={videoRef} muted playsInline />
      {!ready ? <Camera aria-hidden="true" /> : null}
    </div>
  );
}
