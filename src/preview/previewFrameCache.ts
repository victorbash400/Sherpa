const frames = new Map<string, string>();

export function cachedPreviewFrame(taskId: string) {
  return frames.get(taskId);
}

export function cachePreviewFrame(taskId: string, bytes: Uint8Array) {
  const previous = frames.get(taskId);
  if (previous) URL.revokeObjectURL(previous);
  const url = URL.createObjectURL(new Blob([Uint8Array.from(bytes)], { type: "image/jpeg" }));
  frames.set(taskId, url);
  return url;
}
