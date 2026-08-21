import "./CursorDock.css";
import { publicAssetUrl } from "../assets/publicAssetUrl";

export function CursorDock() {
  return (
    <span className="cursor-dock" aria-label="Sherpa computer control" title="Computer control">
      <img alt="" aria-hidden="true" src={publicAssetUrl("cursor-alt-svgrepo-com.svg?v=2")} />
      <span>Computer</span>
    </span>
  );
}
