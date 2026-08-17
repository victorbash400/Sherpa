#!/usr/bin/env node

import assert from "node:assert/strict";
import { updateAppcastEntry } from "./update-appcast-entry.mjs";

const original = `<?xml version="1.0" encoding="utf-8"?>
<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle" version="2.0">
    <channel>
        <language>en</language>
        <item>
            <title>3.9.4</title>
            <sparkle:shortVersionString>3.9.4</sparkle:shortVersionString>
        </item>
        <item>
            <title>Peekaboo 3.9.2</title>
            <enclosure sparkle:shortVersionString="3.9.2" />
        </item>
    </channel>
</rss>
`;

const entry = {
  version: "3.9.5",
  releaseUrl: "https://github.com/openclaw/Peekaboo/releases/tag/v3.9.5",
  assetUrl: "https://github.com/openclaw/Peekaboo/releases/download/v3.9.5/Peekaboo-3.9.5.app.zip",
  buildNumber: "3090599",
  zipLength: "17009920",
  edSignature: "test-signature",
  minimumSystemVersion: "15.0",
  pubDate: "Sat, 18 Jul 2026 20:00:00 +0000",
};

const updated = updateAppcastEntry(original, entry);
assert.equal(updated.match(/sparkle:shortVersionString="3\.9\.5"/g)?.length, 1);
assert.match(updated, /length="17009920"/);
assert.match(updated, /sparkle:edSignature="test-signature"/);
assert.match(updated, /<sparkle:shortVersionString>3\.9\.4<\/sparkle:shortVersionString>/);
assert.match(updated, /sparkle:shortVersionString="3\.9\.2"/);
assert.ok(updated.indexOf("3.9.5") < updated.indexOf("3.9.4"));

const replaced = updateAppcastEntry(updated, {
  ...entry,
  zipLength: "17009921",
  edSignature: "replacement-signature",
});
assert.equal(replaced.match(/sparkle:shortVersionString="3\.9\.5"/g)?.length, 1);
assert.doesNotMatch(replaced, /length="17009920"/);
assert.match(replaced, /length="17009921"/);
assert.match(replaced, /sparkle:edSignature="replacement-signature"/);

console.log("test-update-appcast-entry: ok");
