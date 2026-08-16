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
  const cameraActive = active && settings.signLanguageEnabled;
  return (
    <>
      <h1 className="plugins-view__title">Accessibility</h1>
      <section className="accessibility-view" aria-label="Accessibility">
        <div className="accessibility-section accessibility-sign-language">
          <div className="accessibility-sign-language__settings">
            <header>
              <span><strong>Sign language</strong><small>Use the camera for signed conversations.</small></span>
              <AccessibilitySwitch checked={settings.signLanguageEnabled} label="Sign language" onChange={(signLanguageEnabled) => update({ signLanguageEnabled })} />
            </header>
            <div className="accessibility-row">
              <span><strong>Signing</strong><small>The sign language you use.</small></span>
              <AccessibilitySelect disabled={!settings.signLanguageEnabled} label="Sign language" onChange={(signLanguage) => update({ signLanguage })} options={SIGN_LANGUAGES} value={settings.signLanguage} />
            </div>
          </div>
          <div className="accessibility-preview" data-enabled={settings.signLanguageEnabled}>
            <AccessibilityCamera active={cameraActive} />
          </div>
        </div>
        <div className="accessibility-section accessibility-language">
          <h2>Language</h2>
          <div className="accessibility-row">
            <span><strong>Sherpa speaks</strong><small>The language used for spoken replies.</small></span>
            <AccessibilitySelect label="Spoken language" onChange={(spokenLanguage) => update({ spokenLanguage })} options={SPOKEN_LANGUAGES} value={settings.spokenLanguage} />
          </div>
        </div>
      </section>
    </>
  );
}
