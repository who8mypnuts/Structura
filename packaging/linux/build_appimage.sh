#!/usr/bin/env bash
# Wrap dist/Structura (from packaging/build.py) into an AppImage. Needs appimagetool on PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APPDIR="$ROOT/dist/Structura.AppDir"
rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -a "$ROOT/dist/Structura/." "$APPDIR/usr/bin/"
cp "$ROOT/packaging/linux/structura.desktop" "$APPDIR/io.github.structura.Structura.desktop"
cp "$ROOT/src/structura/resources/brand/png/icon-256.png" "$APPDIR/io.github.structura.Structura.png"
cp "$ROOT/src/structura/resources/brand/png/icon-256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/io.github.structura.Structura.png"
cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
case "$(basename "$ARGV0")" in
  structura) exec "$HERE/usr/bin/structura" "$@" ;;   # symlink the AppImage as 'structura' for the CLI
  *) exec "$HERE/usr/bin/Structura" "$@" ;;
esac
RUN
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 appimagetool "$APPDIR" "$ROOT/dist/Structura-x86_64.AppImage"
