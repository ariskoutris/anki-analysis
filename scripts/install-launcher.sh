#!/usr/bin/env bash
# Builds "Anki Dashboard.app" in ~/Applications, pointing at this checkout.
# Re-run after moving the repo; running it again just rebuilds the app.
set -euo pipefail

APP_NAME="Anki Dashboard"
BUNDLE_ID="io.github.ariskoutris.anki-dashboard"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="${APP_DIR:-$HOME/Applications}/$APP_NAME.app"
LOG="$HOME/Library/Logs/anki-dashboard.log"

[[ "$(uname)" == Darwin ]] || { echo "This launcher is macOS-only." >&2; exit 1; }

# Apps launched from Finder/Spotlight get a minimal PATH, so bake in uv's absolute path.
UV="$(command -v uv || true)"
[[ -n "$UV" ]] || { echo "uv not found. Install it first: https://docs.astral.sh/uv/" >&2; exit 1; }

echo "Installing dependencies..."
"$UV" sync --project "$REPO" --quiet

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Icon: build a multi-resolution .icns from the 1024px PNG using built-in macOS tools.
ICONSET="$(mktemp -d)/icon.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z $size $size "$REPO/assets/icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  sips -z $((size * 2)) $((size * 2)) "$REPO/assets/icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns"
rm -rf "$(dirname "$ICONSET")"

cat > "$APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleExecutable</key><string>launch</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

# exec (rather than `uv run`) keeps Python as the bundle's own process,
# so the Dock shows this app's name and icon instead of a generic Python one.
cat > "$APP/Contents/MacOS/launch" <<EOF
#!/bin/bash
cd "$REPO" || exit 1
"$UV" sync --project "$REPO" --quiet >>"$LOG" 2>&1
exec "$REPO/.venv/bin/python" -m src.desktop >>"$LOG" 2>&1
EOF
chmod +x "$APP/Contents/MacOS/launch"

# Refresh Finder/Dock icon caches for the rebuilt bundle.
touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true

echo "Installed: $APP"
echo "Launch it from Spotlight, Launchpad or Finder. Logs: $LOG"
