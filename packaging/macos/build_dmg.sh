#!/usr/bin/env bash
# Sign, notarise and package dist/Structura.app (from packaging/build.py) as a disk image.
# Environment: STRUCTURA_SIGN_IDENTITY ("Developer ID Application: …"), STRUCTURA_NOTARY_PROFILE (notarytool
# keychain profile). Without them the image is built unsigned (for local testing only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$ROOT/dist/Structura.app"
DMG="$ROOT/dist/Structura.dmg"
if [[ -n "${STRUCTURA_SIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp \
    --entitlements "$ROOT/packaging/macos/entitlements.plist" --sign "$STRUCTURA_SIGN_IDENTITY" "$APP"
fi
rm -f "$DMG"
hdiutil create -volname Structura -srcfolder "$APP" -ov -format UDZO "$DMG"
if [[ -n "${STRUCTURA_NOTARY_PROFILE:-}" ]]; then
  xcrun notarytool submit "$DMG" --keychain-profile "$STRUCTURA_NOTARY_PROFILE" --wait
  xcrun stapler staple "$DMG"
fi
echo "built $DMG"
