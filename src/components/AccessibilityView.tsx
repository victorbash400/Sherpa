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
  const cameraActive = active && settings.enabled && settings.signLanguageEnabled;
  return (
    <>
      <h1 className="plugins-view__title">Accessibility</h1>
      <section className="accessibility-view" aria-label="Accessibility">
        <div className="accessibility-section">
          <div className="accessibility-row">
            <span><strong>Accessibility</strong><small>Adapt Sherpa for signed and multilingual conversations.</small></span>
            <AccessibilitySwitch checked={settings.enabled} label="Accessibility" onChange={(enabled) => update({ enabled })} />
          </div>
          <div className="accessibility-row">
            <span><strong>Sign language</strong><small>Open a camera preview for signed conversations.</small></span>
            <AccessibilitySwitch checked={settings.signLanguageEnabled} label="Sign language" onChange={(signLanguageEnabled) => update({ signLanguageEnabled })} />
          </div>
          <div className="accessibility-row">
            <span><strong>Conversation</strong><small>Choose the signed input and Sherpa's spoken response.</small></span>
            <span>
              <AccessibilitySelect disabled={!settings.enabled} label="Signing" onChange={(signLanguage) => update({ signLanguage })} options={SIGN_LANGUAGES} value={settings.signLanguage} />
              <AccessibilitySelect disabled={!settings.enabled} label="Sherpa speaks" onChange={(spokenLanguage) => update({ spokenLanguage })} options={SPOKEN_LANGUAGES} value={settings.spokenLanguage} />
            </span>
          </div>
        </div>
        <div className="accessibility-section">
          <AccessibilityCamera active={cameraActive} />
        </div>
        <p className="accessibility-note">Sign interpretation is not connected yet. This preview only confirms the camera framing.</p>
      </section>
    </>
  );
}
