import { useEffect, useRef, useState } from "react";
import { Camera } from "lucide-react";
import type { PhotoCaptureResult } from "../hooks/useVoiceSession";
import type { CapturedPhoto } from "./capturedPhotoTypes";
import "./CameraOrbPreview.css";

interface CameraOrbPreviewProps {
  active: boolean;
  captureRequest?: { callId: string };
  onCaptured: (photo: CapturedPhoto) => void;
  onCaptureResult: (callId: string, result: PhotoCaptureResult) => void;
  onFrame: (data: string, mimeType: string) => void;
  onError: (message?: string) => void;
}

type VideoWithFrameCallbacks = HTMLVideoElement & {
  requestVideoFrameCallback: (callback: (now: number) => void) => number;
  cancelVideoFrameCallback: (handle: number) => void;
};

export function CameraOrbPreview({ active, captureRequest, onCaptured, onCaptureResult, onError, onFrame }: CameraOrbPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const frameCallbackRef = useRef<number | undefined>(undefined);
  const encodingRef = useRef(false);
  const lastFrameAtRef = useRef(0);
  const shutterRef = useRef<HTMLAudioElement | undefined>(undefined);
  const [ready, setReady] = useState(false);
  const [flashing, setFlashing] = useState(false);
  const capturedCallRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!captureRequest || capturedCallRef.current === captureRequest.callId) return;
    capturedCallRef.current = captureRequest.callId;
    const video = videoRef.current;
    if (!active || !ready || !video?.videoWidth || !window.sherpaPhotos) {
      onCaptureResult(captureRequest.callId, {
        status: "failed",
        error: active ? "The camera is not ready yet." : "Turn the camera on before taking a photo.",
      });
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) {
      onCaptureResult(captureRequest.callId, { status: "failed", error: "The photo could not be rendered." });
      return;
    }
    context.drawImage(video, 0, 0);
    const shutter = shutterRef.current;
    if (shutter) {
      shutter.currentTime = 0;
      void shutter.play().catch(() => undefined);
    }
    setFlashing(true);
    window.setTimeout(() => setFlashing(false), 320);
    canvas.toBlob((blob) => {
      if (!blob) {
        onCaptureResult(captureRequest.callId, { status: "failed", error: "The photo could not be encoded." });
        return;
      }
      void blob.arrayBuffer()
        .then((buffer) => window.sherpaPhotos?.save(new Uint8Array(buffer)))
        .then((photoPath) => {
          if (!photoPath) throw new Error("The photo could not be saved.");
          const mimeType = blob.type || "image/jpeg";
          onCaptured({
            id: captureRequest.callId,
            mimeType,
            path: photoPath,
            previewUrl: URL.createObjectURL(blob),
            sourceBounds: video.getBoundingClientRect().toJSON(),
          });
          onCaptureResult(captureRequest.callId, { status: "captured", path: photoPath, mimeType });
        })
        .catch((reason: unknown) => {
          onCaptureResult(captureRequest.callId, {
            status: "failed",
            error: reason instanceof Error ? reason.message : "The photo could not be saved.",
          });
        });
    }, "image/jpeg", 0.94);
  }, [active, captureRequest, onCaptured, onCaptureResult, ready]);

  useEffect(() => {
    const shutter = new Audio("/irinairinafomicheva-camera-13695.mp3");
    shutter.preload = "auto";
    shutter.volume = 0.72;
    shutter.load();
    shutterRef.current = shutter;
    return () => {
      shutter.pause();
      shutterRef.current = undefined;
    };
  }, []);

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
    <div className="camera-orb-preview" data-flashing={flashing} data-ready={ready} aria-hidden={!active}>
      <video ref={videoRef} muted playsInline />
      {!ready ? <Camera aria-hidden="true" /> : null}
    </div>
  );
}
