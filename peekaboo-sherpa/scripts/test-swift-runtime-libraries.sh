#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEST_DIR=$(mktemp -d /tmp/peekaboo-swift-runtime-test.XXXXXX)
trap 'rm -rf "$TEST_DIR"' EXIT

printf '%s\n' 'print(OutputSpan<UInt8>.self)' > "$TEST_DIR/SpanProbe.swift"
xcrun swiftc \
    -target "$(uname -m)-apple-macosx15.0" \
    -Xlinker -rpath \
    -Xlinker @loader_path \
    "$TEST_DIR/SpanProbe.swift" \
    -o "$TEST_DIR/span-probe"

if ! otool -L "$TEST_DIR/span-probe" | grep -Fq '@rpath/libswiftCompatibility'; then
    echo "test-swift-runtime-libraries: active toolchain emitted no compatibility dependency; skipped"
    exit 0
fi

if "$ROOT_DIR/scripts/verify-swift-runtime-libraries.sh" "$TEST_DIR/span-probe" "$TEST_DIR" >/dev/null 2>&1; then
    echo "Verifier accepted a dangling Swift compatibility dependency" >&2
    exit 1
fi

"$ROOT_DIR/scripts/copy-swift-runtime-libraries.sh" "$TEST_DIR/span-probe" "$TEST_DIR"
"$TEST_DIR/span-probe" >/dev/null

echo "test-swift-runtime-libraries: ok"
