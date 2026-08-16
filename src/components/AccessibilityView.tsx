import type { AccessibilitySettings } from "../accessibility/accessibilitySettings";
import { SIGN_LANGUAGES, SPOKEN_LANGUAGES } from "../accessibility/accessibilitySettings";
import { AccessibilityCamera } from "./AccessibilityCamera";
import { AccessibilitySelect } from "./AccessibilitySelect";
import { AccessibilitySwitch } from "./AccessibilitySwitch";
import "./PluginsView.css";
import "./AccessibilityView.css";

interface AccessibilityViewProps {
  active: boolean;
  onChange: (settings: AccessibilitySettings) => void;
  settings: AccessibilitySettings;
}

export function AccessibilityView({ active, onChange, settings }: AccessibilityViewProps) {
  const update = (change: Partial<AccessibilitySettings>) => onChange({ ...settings, ...change });
  const cameraActive = active && settings.cameraEnabled;
  return (
    <>
      <h1 className="plugins-view__title">Accessibility</h1>
      <section className="accessibility-view" aria-label="Accessibility">
        <div className="accessibility-settings">
          <h2>Sign language</h2>
          <div className="accessibility-row">
            <span><strong>Signing</strong><small>The sign language you use.</small></span>
            <AccessibilitySelect label="Sign language" onChange={(signLanguage) => update({ signLanguage })} options={SIGN_LANGUAGES} value={settings.signLanguage} />
          </div>
          <div className="accessibility-row">
            <span><strong>Sherpa speaks</strong><small>The language used for spoken replies.</small></span>
            <AccessibilitySelect label="Spoken language" onChange={(spokenLanguage) => update({ spokenLanguage })} options={SPOKEN_LANGUAGES} value={settings.spokenLanguage} />
          </div>
          <div className="accessibility-row">
            <span><strong>Camera</strong><small>Show the signing preview.</small></span>
            <AccessibilitySwitch checked={settings.cameraEnabled} label="Camera" onChange={(cameraEnabled) => update({ cameraEnabled })} />
          </div>
        </div>
        <div className="accessibility-preview">
          <AccessibilityCamera active={cameraActive} />
          <small>Camera preview</small>
        </div>
      </section>
    </>
  );
}
