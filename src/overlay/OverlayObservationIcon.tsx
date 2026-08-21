import "./OverlayObservationIcon.css";
import { publicAssetUrl } from "../assets/publicAssetUrl";

interface OverlayObservationIconProps {
  action?: string;
}

export function OverlayObservationIcon({ action }: OverlayObservationIconProps) {
  if (!["computer_see", "computer_inspect_ui", "browser_snapshot", "browser_find"].includes(action || "")) return null;

  return (
    <img
      className="overlay-observation-icon"
      src={publicAssetUrl("reading-glasses-specs-vision-svgrepo-com.svg")}
      alt=""
      aria-hidden="true"
    />
  );
}
