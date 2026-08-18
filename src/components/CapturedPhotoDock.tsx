import { Maximize2, Minimize2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { CapturedPhoto } from "./capturedPhotoTypes";
import "./CapturedPhotoDock.css";

interface CapturedPhotoDockProps {
  photo: CapturedPhoto;
  onClose: () => void;
}

export function CapturedPhotoDock({ onClose, photo }: CapturedPhotoDockProps) {
  const dockRef = useRef<HTMLElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [arriving, setArriving] = useState(true);

  useEffect(() => {
    const target = dockRef.current?.getBoundingClientRect();
    if (!target || matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setArriving(false);
      return;
    }
    setExpanded(false);
    setArriving(true);
    const flyingPhoto = document.createElement("img");
    flyingPhoto.className = "captured-photo-flight";
    flyingPhoto.src = photo.previewUrl;
    document.body.append(flyingPhoto);
    const source = photo.sourceBounds;
    const animation = flyingPhoto.animate([
      { left: `${source.x}px`, top: `${source.y}px`, width: `${source.width}px`, height: `${source.height}px`, borderRadius: "50%", opacity: 1, offset: 0 },
      { left: `${source.x - 8}px`, top: `${source.y - 8}px`, width: `${source.width + 16}px`, height: `${source.height + 16}px`, borderRadius: "42%", opacity: 1, offset: .18 },
      { left: `${target.x - 4}px`, top: `${target.y - 4}px`, width: `${target.width + 8}px`, height: `${target.height + 8}px`, borderRadius: "18px", opacity: 1, offset: .86 },
      { left: `${target.x}px`, top: `${target.y}px`, width: `${target.width}px`, height: `${target.height}px`, borderRadius: "16px", opacity: 1, offset: 1 },
    ], { duration: 980, easing: "cubic-bezier(.22,1,.36,1)", fill: "forwards" });
    animation.addEventListener("finish", () => {
      flyingPhoto.remove();
      setArriving(false);
    }, { once: true });
    return () => flyingPhoto.remove();
  }, [photo]);

  return (
    <section ref={dockRef} className="captured-photo-dock" data-arriving={arriving} data-expanded={expanded} aria-label="Latest captured photo">
      <img alt="Latest photo captured by Sherpa" src={photo.previewUrl} />
      <button className="captured-photo-dock__close" type="button" onClick={onClose} aria-label="Dismiss captured photo">
        <X aria-hidden="true" />
      </button>
      <button className="captured-photo-dock__expand" type="button" onClick={() => setExpanded((current) => !current)} aria-label={expanded ? "Contract captured photo" : "Expand captured photo"}>
        {expanded ? <Minimize2 aria-hidden="true" /> : <Maximize2 aria-hidden="true" />}
      </button>
    </section>
  );
}
