import { useEffect, useRef, useState } from "react";
import { Camera } from "lucide-react";

interface AccessibilityCameraProps {
  active: boolean;
}

export function AccessibilityCamera({ active }: AccessibilityCameraProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (!active) return;
    let stream: MediaStream | undefined;
    let cancelled = false;
    void navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: 640, height: 360 } })
      .then((nextStream) => {
        if (cancelled) {
          nextStream.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = nextStream;
        if (videoRef.current) videoRef.current.srcObject = nextStream;
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Camera access failed.");
      });
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((track) => track.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [active]);

  if (!active) {
    return <div className="accessibility-camera accessibility-camera--idle"><Camera aria-hidden="true" /><span>Camera off</span></div>;
  }

  if (error) return <p className="accessibility-camera__error" role="alert">{error}</p>;
  return <video aria-label="Sign language camera preview" autoPlay className="accessibility-camera" muted playsInline ref={videoRef} />;
}
