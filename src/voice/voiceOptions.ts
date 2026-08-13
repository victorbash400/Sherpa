export type VoiceOption = {
  id: string;
  name: string;
  description: string;
  hue: number;
};

export const voiceOptions: VoiceOption[] = [
  { id: "Kore", name: "Kore", description: "Firm", hue: 0 },
  { id: "Aoede", name: "Aoede", description: "Breezy", hue: 38 },
  { id: "Leda", name: "Leda", description: "Youthful", hue: 75 },
  { id: "Zephyr", name: "Zephyr", description: "Bright", hue: 128 },
  { id: "Puck", name: "Puck", description: "Upbeat", hue: 178 },
  { id: "Charon", name: "Charon", description: "Informative", hue: 220 },
  { id: "Fenrir", name: "Fenrir", description: "Excitable", hue: 262 },
  { id: "Orus", name: "Orus", description: "Firm", hue: 304 },
  { id: "Sulafat", name: "Sulafat", description: "Warm", hue: 338 },
];

export function loadVoice(): VoiceOption {
  const saved = window.localStorage.getItem("sherpa-voice");
  return voiceOptions.find((voice) => voice.id === saved) ?? voiceOptions[0];
}

export function saveVoice(voice: VoiceOption) {
  window.localStorage.setItem("sherpa-voice", voice.id);
}
