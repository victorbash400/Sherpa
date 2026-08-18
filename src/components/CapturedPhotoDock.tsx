import { useEffect, useRef, useState } from "react";
import type { CapturedPhoto } from "./capturedPhotoTypes";
import { CapturedPhotoViewer } from "./CapturedPhotoViewer";
import "./CapturedPhotoDock.css";

interface CapturedPhotoDockProps { photo: CapturedPhoto }

export function CapturedPhotoDock({ photo }: CapturedPhotoDockProps) {
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const target = buttonRef.current?.getBoundingClientRect();
    if (!target || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const flyingPhoto = document.createElement("img");
    flyingPhoto.className = "captured-photo-flight";
    flyingPhoto.src = photo.previewUrl;
    document.body.append(flyingPhoto);
    const source = photo.sourceBounds;
    const animation = flyingPhoto.animate([
      { left: `${source.x}px`, top: `${source.y}px`, width: `${source.width}px`, height: `${source.height}px`, borderRadius: "50%", opacity: 1 },
      { left: `${target.x}px`, top: `${target.y}px`, width: `${target.width}px`, height: `${target.height}px`, borderRadius: "12px", opacity: 1 },
    ], { duration: 520, easing: "cubic-bezier(.2,.8,.2,1)", fill: "forwards" });
    animation.addEventListener("finish", () => flyingPhoto.remove(), { once: true });
    return () => flyingPhoto.remove();
  }, [photo]);

  return (
    <>
      <button ref={buttonRef} className="captured-photo-dock" type="button" onClick={() => setExpanded(true)} aria-label="Expand latest captured photo">
        <img alt="" src={photo.previewUrl} />
      </button>
      {expanded ? <CapturedPhotoViewer photo={photo} onClose={() => setExpanded(false)} /> : null}
    </>
  );
}
