import "./RefreshButton.css";
import { publicAssetUrl } from "../assets/publicAssetUrl";

export function RefreshButton() {
  return (
    <button
      className="refresh-button"
      aria-label="Refresh Sherpa"
      onClick={() => window.location.reload()}
      type="button"
    >
      <img alt="" aria-hidden="true" src={publicAssetUrl("reload-ui-svgrepo-com.svg")} />
    </button>
  );
}
