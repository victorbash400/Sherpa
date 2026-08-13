export type VoiceOption = {
  id: string;
  name: string;
  description: string;
  hue: number;
};

export const voiceOptions: VoiceOption[] = [
  { id: "Kore", name: "Kore", description: "Firm, feminine", hue: 0 },
  { id: "Aoede", name: "Aoede", description: "Breezy, feminine", hue: 38 },
  { id: "Leda", name: "Leda", description: "Youthful, feminine", hue: 75 },
  { id: "Zephyr", name: "Zephyr", description: "Bright, feminine", hue: 128 },
  { id: "Puck", name: "Puck", description: "Upbeat, masculine", hue: 178 },
  { id: "Charon", name: "Charon", description: "Informative, masculine", hue: 220 },
  { id: "Fenrir", name: "Fenrir", description: "Excitable, masculine", hue: 262 },
  { id: "Orus", name: "Orus", description: "Firm, masculine", hue: 304 },
  { id: "Sulafat", name: "Sulafat", description: "Warm, feminine", hue: 338 },
];

export function loadVoice(): VoiceOption {
  const saved = window.localStorage.getItem("sherpa-voice");
  return voiceOptions.find((voice) => voice.id === saved) ?? voiceOptions[0];
}

export function saveVoice(voice: VoiceOption) {
  window.localStorage.setItem("sherpa-voice", voice.id);
}
