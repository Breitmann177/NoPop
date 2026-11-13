"""NoPop-Logo: silberne, unterbrochene Ringe
um einen Punkt – wie Schallwellen. Kein Hintergrund.

Kleine Größen (Tray/Taskleiste, 16–48 px) werden pro Größe einzeln auf
ganze Pixel ausgerichtet gezeichnet, damit nichts verschwimmt.
"""
import math
import os

from PIL import Image, ImageDraw

# Akzentfarben fürs Tray-Symbol, wenn die Lautsprecher wach gehalten werden
FARBEN = {
    "silber": (236, 236, 240),
    "gruen": (85, 211, 117),
    "blau": (79, 156, 240),
    "lila": (165, 124, 240),
    "orange": (243, 158, 67),
    "rot": (234, 96, 96),
}

# ---------------------------------------------------------------- große Version
SS = 4


def _silber(S):
    """Silberverlauf: oben hell, unten dunkleres Grau."""
    g = Image.new("RGB", (1, S))
    for y in range(S):
        t = y / (S - 1)
        g.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip((222, 222, 226), (140, 140, 148))))
    return g.resize((S, S))


def _bogen(d, c, r, w, a0, a1, alpha, rund=True):
    """Bogen mit Mittellinie r und Breite w (Winkel in Grad, im Uhrzeigersinn ab 3 Uhr)."""
    R = r + w / 2
    d.arc((c - R, c - R, c + R, c + R), a0, a1, fill=alpha, width=max(1, round(w)))
    if rund:
        for a in (a0, a1):
            x, y = c + r * math.cos(math.radians(a)), c + r * math.sin(math.radians(a))
            d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=alpha)


# Ringe: (Radius, Breite, Deckkraft, Segmente, Drehung) – innen kräftig, außen leiser
GROSS = [(0.175, 0.046, 255, 3, 20), (0.265, 0.046, 232, 4, 62),
         (0.355, 0.046, 200, 5, 8), (0.445, 0.046, 165, 6, 41)]


def gross(size):
    S = size * SS
    c = S / 2
    maske = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(maske)
    for r, w, a, n, dreh in GROSS:
        R, W = r * S, w * S
        luecke = math.degrees((W * 1.6) / R)  # gleich breite Lücken
        teil = 360 / n
        for i in range(n):
            _bogen(d, c, R, W, dreh + i * teil + luecke / 2, dreh + (i + 1) * teil - luecke / 2, a)
    p = 0.072 * S
    d.ellipse((c - p, c - p, c + p, c + p), fill=255)
    bild = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bild.paste(_silber(S).convert("RGBA"), (0, 0), maske)
    return bild.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- kleine Versionen
# pro Größe: Punkt-Radius, [(Ring-Mitte, Breite, Segmente, Drehung)] – Kanten auf ganzen Pixeln
KLEIN = {
    16: (2.0, [(4.75, 1.5, 3, 30), (7.25, 1.5, 4, 0)]),
    20: (2.0, [(5.5, 2.0, 3, 30), (8.5, 2.0, 4, 0)]),
    24: (2.5, [(6.5, 2.0, 3, 30), (10.5, 2.0, 4, 0)]),
    28: (3.0, [(7.5, 2.5, 3, 30), (12.0, 2.5, 4, 0)]),
    32: (3.5, [(8.5, 3.0, 3, 30), (13.5, 3.0, 4, 0)]),
    36: (4.0, [(9.5, 3.0, 3, 30), (15.0, 3.0, 4, 0)]),
    40: (4.0, [(10.5, 3.0, 3, 30), (16.5, 3.0, 4, 0)]),
    48: (5.0, [(12.5, 4.0, 3, 30), (20.0, 4.0, 4, 0)]),
}


def klein(size, farbe):
    """Flaches, pixelgenaues Symbol in einer Farbe."""
    punkt, ringe = KLEIN[size]
    S = size * 8
    c = S / 2
    maske = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(maske)
    for r, w, n, dreh in ringe:
        R, W = r * 8, w * 8
        luecke = math.degrees((max(1.2, w * 0.75) * 8) / R)
        teil = 360 / n
        for i in range(n):
            _bogen(d, c, R, W, dreh + i * teil + luecke / 2, dreh + (i + 1) * teil - luecke / 2, 255, rund=False)
    p = punkt * 8
    d.ellipse((c - p, c - p, c + p, c + p), fill=255)
    maske = maske.resize((size, size), Image.BOX)
    # Kanten schärfen: halbtransparente Randpixel deutlich reduzieren
    maske = maske.point(lambda v: 0 if v <= 60 else 255 if v >= 190 else (v - 60) * 255 // 130)
    bild = Image.new("RGBA", (size, size), farbe + (0,))
    bild.putalpha(maske)
    return bild


def _ico(pfad, bilder):
    groessen = sorted(bilder)
    bilder[groessen[-1]].save(pfad, format="ICO", sizes=[(g, g) for g in groessen],
                              append_images=[bilder[g] for g in groessen[:-1]])


def speichere_alles(ordner):
    os.makedirs(ordner, exist_ok=True)
    # App-Symbol (Fenster, Startmenü): klein = pixelgenau in Silbergrau, groß = voller Verlauf
    app = {g: klein(g, (200, 200, 208)) for g in KLEIN}
    app.update({g: gross(g) for g in (64, 128, 256)})
    _ico(os.path.join(ordner, "nopop.ico"), app)
    gross(512).save(os.path.join(ordner, "logo-512.png"))
    # Tray-Symbole je Taskleisten-Design (dunkel/hell) und Zustand
    for design, aus_farbe in (("dunkel", (150, 150, 156)), ("hell", (110, 110, 116))):
        _ico(os.path.join(ordner, f"tray-aus-{design}.ico"), {g: klein(g, aus_farbe) for g in KLEIN})
        for name, farbe in FARBEN.items():
            if design == "hell":
                farbe = (40, 40, 44) if name == "silber" else tuple(int(x * 0.78) for x in farbe)
            _ico(os.path.join(ordner, f"tray-{name}-{design}.ico"), {g: klein(g, farbe) for g in KLEIN})


if __name__ == "__main__":
    hier = os.path.dirname(os.path.abspath(__file__))
    speichere_alles(os.path.join(hier, "assets"))
    print("ok")
