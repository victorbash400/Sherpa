import { useEffect, useState } from "react";
import { Play, X } from "lucide-react";
import "./PetsView.css";

export function PetsView({ active }: { active: boolean }) {
  const [awake, setAwake] = useState(false);

  useEffect(() => {
    if (active) void window.sherpaPet?.isAwake().then(setAwake);
    return window.sherpaPet?.onStateChanged(setAwake);
  }, [active]);

  const toggle = async () => {
    if (awake) {
      window.sherpaPet?.sleep();
      setAwake(false);
      return;
    }
    setAwake(Boolean(await window.sherpaPet?.wake()));
  };

  return (
    <section className="pets-view" aria-label="Desktop pets">
      <header>
        <h1>Pets</h1>
        <p>Keep a small companion around while Sherpa works.</p>
      </header>
      <article className="pet-card">
        <img
          alt="Blue monster desktop pet"
          src={new URL(
            "monster_desktop_pet_sprite_bundle/frames_png/frame_10_idle_subtle_breathing_rise.png",
            document.baseURI,
          ).toString()}
        />
        <span>
          <strong>Monster</strong>
          <small>{awake ? "Chilling on your desktop" : "Ready to join you"}</small>
        </span>
        <button type="button" onClick={() => void toggle()}>
          {awake ? <X aria-hidden="true" /> : <Play aria-hidden="true" />}
          {awake ? "Put away" : "Launch"}
        </button>
      </article>
    </section>
  );
}
