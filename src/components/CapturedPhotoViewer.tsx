import { X } from "lucide-react";
import type { CapturedPhoto } from "./capturedPhotoTypes";
import "./CapturedPhotoViewer.css";

interface CapturedPhotoViewerProps {
  photo: CapturedPhoto;
  onClose: () => void;
}

export function CapturedPhotoViewer({ onClose, photo }: CapturedPhotoViewerProps) {
  return (
    <section className="captured-photo-viewer" aria-label="Captured photo preview">
      <button type="button" aria-label="Close photo" onClick={onClose}><X aria-hidden="true" /></button>
      <img alt="Latest photo captured by Sherpa" src={photo.previewUrl} />
    </section>
  );
}
