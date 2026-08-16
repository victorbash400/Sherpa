export const SIGN_LANGUAGES = [
  { id: "asl", label: "American Sign Language" },
  { id: "bsl", label: "British Sign Language" },
  { id: "ksl", label: "Kenyan Sign Language" },
  { id: "auslan", label: "Auslan" },
  { id: "isl", label: "International Sign" },
] as const;

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
  enabled: boolean;
  signLanguage: string;
  signLanguageEnabled: boolean;
  spokenLanguage: string;
};

export const DEFAULT_ACCESSIBILITY_SETTINGS: AccessibilitySettings = {
  enabled: false,
  signLanguage: "asl",
  signLanguageEnabled: false,
  spokenLanguage: "en",
};

export function loadAccessibilitySettings(): AccessibilitySettings {
  try {
    const stored = JSON.parse(localStorage.getItem("sherpa.accessibility") || "null") as Partial<AccessibilitySettings> | null;
    return stored ? { ...DEFAULT_ACCESSIBILITY_SETTINGS, ...stored } : DEFAULT_ACCESSIBILITY_SETTINGS;
  } catch {
    return DEFAULT_ACCESSIBILITY_SETTINGS;
  }
}

export function saveAccessibilitySettings(settings: AccessibilitySettings) {
  localStorage.setItem("sherpa.accessibility", JSON.stringify(settings));
}
