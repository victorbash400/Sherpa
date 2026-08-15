export interface MemorySettingsValues {
  enabled: boolean;
  learn_from_tools: boolean;
  custom_instructions: string;
  chat_style: string;
  response_style: string;
}

export interface MemoryItem {
  id: string;
  category: string;
  content: string;
  source_type: string;
  editable: boolean;
  active: boolean;
  updated_at: string;
}

export interface MemorySnapshot {
  settings: MemorySettingsValues;
  memories: MemoryItem[];
  limits: Record<"custom_instructions" | "chat_style" | "response_style", number>;
}
