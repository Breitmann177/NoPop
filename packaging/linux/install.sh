#!/bin/sh
# NoPop installer for Linux – current user only. Run:  ./install.sh
set -e
cd "$(dirname "$0")"
case "${LANG:-}${LC_ALL:-}" in de*|*de_*) DE=1 ;; *) DE= ;; esac
say() { if [ -n "$DE" ]; then echo "$1"; else echo "$2"; fi; }

# --- what NoPop needs: python3, tkinter, pactl/pacat (PipeWire or PulseAudio)
fehlt=
command -v python3 >/dev/null 2>&1 || fehlt=1
python3 -c "import tkinter" 2>/dev/null || fehlt=1
command -v pactl >/dev/null 2>&1 || fehlt=1
if [ -n "$fehlt" ]; then
    if   command -v apt-get >/dev/null; then cmd="sudo apt-get install -y python3 python3-tk pulseaudio-utils"
    elif command -v dnf     >/dev/null; then cmd="sudo dnf install -y python3 python3-tkinter pulseaudio-utils"
    elif command -v pacman  >/dev/null; then cmd="sudo pacman -S --needed --noconfirm python tk libpulse"
    elif command -v zypper  >/dev/null; then cmd="sudo zypper install -y python3 python3-tk pulseaudio-utils"
    else
        say "Bitte installiere: Python 3, Tkinter und pactl (pulseaudio-utils). Dann ./install.sh erneut starten." \
            "Please install: Python 3, Tkinter and pactl (pulseaudio-utils). Then run ./install.sh again."
        exit 1
    fi
    say "NoPop braucht noch ein paar kleine Pakete:" "NoPop needs a few small packages:"
    echo "  $cmd"
    printf "%s" "$(say 'Jetzt installieren? [J/n] ' 'Install now? [Y/n] ')"
    read -r a
    case "$a" in n*|N*) exit 1 ;; esac
    $cmd
fi

ZIEL="$HOME/.local/share/nopop"
pkill -f "$ZIEL/nopop.py" 2>/dev/null || true
rm -rf "$ZIEL"
mkdir -p "$ZIEL/assets" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/512x512/apps"
cp nopop.py kern.py kern_linux.py system_linux.py texte.py VERSION LICENSE uninstall.sh "$ZIEL/"
cp assets/logo-512.png "$ZIEL/assets/"
cp assets/logo-512.png "$HOME/.local/share/icons/hicolor/512x512/apps/nopop.png"
chmod +x "$ZIEL/uninstall.sh"

cat > "$HOME/.local/share/applications/nopop.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=NoPop
Comment=Keeps your speakers awake so they don't pop
Comment[de]=Hält die Lautsprecher wach, damit nichts ploppt
Exec=python3 "$ZIEL/nopop.py"
Icon=nopop
Categories=AudioVideo;Audio;Utility;
Terminal=false
DESKTOP
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

nohup python3 "$ZIEL/nopop.py" >/dev/null 2>&1 &
say "Fertig! NoPop läuft und startet ab jetzt automatisch. Öffnen: App-Menü → NoPop." \
    "Done! NoPop is running and starts automatically from now on. Open it: app menu → NoPop."
say "Deinstallieren: $ZIEL/uninstall.sh" "Uninstall: $ZIEL/uninstall.sh"
