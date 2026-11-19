#!/bin/sh
# Removes everything NoPop created.
ZIEL="$HOME/.local/share/nopop"
pkill -f "$ZIEL/nopop.py" 2>/dev/null || true
rm -f "$HOME/.local/share/applications/nopop.desktop" \
      "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/nopop.desktop" \
      "$HOME/.local/share/icons/hicolor/512x512/apps/nopop.png"
rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/NoPop" "$ZIEL"
echo "NoPop removed / entfernt."
