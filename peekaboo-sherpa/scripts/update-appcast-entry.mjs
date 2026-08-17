#!/usr/bin/env node

import fs from "node:fs";
import { pathToFileURL } from "node:url";

const itemPattern = /^[ \t]*<item>[\s\S]*?^[ \t]*<\/item>[ \t]*(?:\r?\n)?/gm;

function containsVersion(item, version) {
  return item.includes(`sparkle:shortVersionString="${version}"`) ||
    item.includes(`<sparkle:shortVersionString>${version}</sparkle:shortVersionString>`);
}

export function updateAppcastEntry(xml, entry) {
  const existingItems = [...xml.matchAll(itemPattern)];
  const firstIndent = existingItems[0]?.[0].match(/^([ \t]*)<item>/)?.[1] ?? "        ";
  const childIndent = `${firstIndent}    `;
  const item = `${firstIndent}<item>
${childIndent}<title>Peekaboo ${entry.version}</title>
${childIndent}<link>${entry.releaseUrl}</link>
${childIndent}<sparkle:releaseNotesLink>${entry.releaseUrl}</sparkle:releaseNotesLink>
${childIndent}<pubDate>${entry.pubDate}</pubDate>
${childIndent}<enclosure
${childIndent}  url="${entry.assetUrl}"
${childIndent}  sparkle:version="${entry.buildNumber}"
${childIndent}  sparkle:shortVersionString="${entry.version}"
${childIndent}  sparkle:minimumSystemVersion="${entry.minimumSystemVersion}"
${childIndent}  length="${entry.zipLength}"
${childIndent}  type="application/octet-stream"
${childIndent}  sparkle:edSignature="${entry.edSignature}" />
${firstIndent}</item>`;

  const withoutCurrentVersion = xml.replace(itemPattern, (existingItem) =>
    containsVersion(existingItem, entry.version) ? "" : existingItem);
  const nextFirstItem = withoutCurrentVersion.match(itemPattern)?.[0];

  if (nextFirstItem) {
    return withoutCurrentVersion.replace(nextFirstItem, `${item}\n${nextFirstItem}`);
  }

  const languagePattern = /(<language>en<\/language>[ \t]*\r?\n)/;
  if (!languagePattern.test(withoutCurrentVersion)) {
    throw new Error("Appcast channel is missing <language>en</language>");
  }
  return withoutCurrentVersion.replace(languagePattern, `$1${item}\n`);
}

function requiredEnvironment(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const appcastPath = requiredEnvironment("APPCAST_PATH");
  const xml = fs.readFileSync(appcastPath, "utf8");
  const updated = updateAppcastEntry(xml, {
    version: requiredEnvironment("VERSION"),
    releaseUrl: requiredEnvironment("RELEASE_URL"),
    assetUrl: requiredEnvironment("ASSET_URL"),
    buildNumber: requiredEnvironment("BUILD_NUMBER"),
    zipLength: requiredEnvironment("ZIP_LENGTH"),
    edSignature: requiredEnvironment("ED_SIGNATURE"),
    minimumSystemVersion: requiredEnvironment("MINIMUM_SYSTEM_VERSION"),
    pubDate: new Date().toUTCString().replace("GMT", "+0000"),
  });
  fs.writeFileSync(appcastPath, updated);
}
