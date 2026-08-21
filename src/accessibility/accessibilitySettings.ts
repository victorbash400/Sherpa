export const SPOKEN_LANGUAGES = [
  { id: "en", label: "English" },
  { id: "sw", label: "Swahili" },
  { id: "fr", label: "French" },
  { id: "de", label: "German" },
  { id: "es", label: "Spanish" },
  { id: "pt", label: "Portuguese" },
  { id: "ar", label: "Arabic" },
  { id: "hi", label: "Hindi" },
  { id: "zh", label: "Chinese" },
  { id: "ja", label: "Japanese" },
  { id: "ko", label: "Korean" },
  { id: "zu", label: "Zulu" },
] as const;

export type AccessibilitySettings = {
  spokenLanguage: string;
};

export const DEFAULT_ACCESSIBILITY_SETTINGS: AccessibilitySettings = {
  spokenLanguage: "en",
};

export function loadAccessibilitySettings(accountId: string): AccessibilitySettings {
  try {
    const stored = JSON.parse(localStorage.getItem(`sherpa.accessibility:${accountId}`) || "null") as Partial<AccessibilitySettings> | null;
    if (!stored) return DEFAULT_ACCESSIBILITY_SETTINGS;
    return {
      spokenLanguage: stored.spokenLanguage ?? DEFAULT_ACCESSIBILITY_SETTINGS.spokenLanguage,
    };
  } catch {
    return DEFAULT_ACCESSIBILITY_SETTINGS;
  }
}

export function saveAccessibilitySettings(accountId: string, settings: AccessibilitySettings) {
  localStorage.setItem(`sherpa.accessibility:${accountId}`, JSON.stringify(settings));
}
