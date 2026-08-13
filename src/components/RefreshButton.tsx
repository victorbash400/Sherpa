import "./RefreshButton.css";

export function RefreshButton() {
  return (
    <button
      className="refresh-button"
      aria-label="Refresh Sherpa"
      onClick={() => window.location.reload()}
      type="button"
    >
      <img alt="" aria-hidden="true" src="/reload-ui-svgrepo-com.svg" />
    </button>
  );
}
