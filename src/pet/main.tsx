import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { DesktopPet } from "./DesktopPet";

createRoot(document.getElementById("pet-root")!).render(
  <StrictMode>
    <DesktopPet />
  </StrictMode>,
);
