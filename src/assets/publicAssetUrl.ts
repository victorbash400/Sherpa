export function publicAssetUrl(path: string): string {
  return new URL(path, document.baseURI).href;
}
