import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AgentCursorOverlay } from "./AgentCursorOverlay";

createRoot(document.getElementById("overlay-root")!).render(
  <StrictMode>
    <AgentCursorOverlay />
  </StrictMode>,
);
