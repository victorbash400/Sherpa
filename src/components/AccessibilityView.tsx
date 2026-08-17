import type { AccessibilitySettings } from "../accessibility/accessibilitySettings";
import { SPOKEN_LANGUAGES } from "../accessibility/accessibilitySettings";
import { AccessibilitySelect } from "./AccessibilitySelect";
import "./PluginsView.css";
import "./AccessibilityView.css";

interface AccessibilityViewProps {
  onChange: (settings: AccessibilitySettings) => void;
  settings: AccessibilitySettings;
}

export function AccessibilityView({ onChange, settings }: AccessibilityViewProps) {
  const update = (change: Partial<AccessibilitySettings>) => onChange({ ...settings, ...change });
  return (
    <>
      <h1 className="plugins-view__title">Accessibility</h1>
      <section className="accessibility-view" aria-label="Accessibility">
        <div className="accessibility-section accessibility-language">
          <h2>Language</h2>
          <div className="accessibility-row">
            <span><strong>Sherpa speaks</strong><small>The language used for spoken replies in voice conversations.</small></span>
            <AccessibilitySelect label="Spoken language" onChange={(spokenLanguage) => update({ spokenLanguage })} options={SPOKEN_LANGUAGES} value={settings.spokenLanguage} />
          </div>
        </div>
      </section>
    </>
  );
}
