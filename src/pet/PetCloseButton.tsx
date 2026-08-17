import { X } from "lucide-react";
import "./PetCloseButton.css";

export function PetCloseButton({ onClose }: { onClose: () => void }) {
  return (
    <button className="pet-close-button" type="button" aria-label="Close pet" onClick={onClose}>
      <X aria-hidden="true" />
    </button>
  );
}
