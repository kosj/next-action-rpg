"""Generate original offline placeholder SFX and an ambient pad; no third-party samples."""
from pathlib import Path
import math
import random
import struct
import wave

OUT = Path(__file__).resolve().parents[1] / "game/assets/audio"
OUT.mkdir(parents=True, exist_ok=True)
RATE = 22050
random.seed(41)


def render(name, duration, func):
    with wave.open(str(OUT / (name + ".wav")), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, func(i / RATE, duration))) * 20000)) for i in range(int(duration * RATE))))


def sfx(t, d, pitch, noise=0.25):
    env = min(1, t * 100) * (1 - t / d) ** 2
    return env * (math.sin(t * math.tau * pitch * (1 - t / d * 0.6)) * (1 - noise) + random.uniform(-1, 1) * noise)


render("slash", 0.22, lambda t, d: sfx(t, d, 420, 0.8))
render("hit", 0.18, lambda t, d: sfx(t, d, 100, 0.5))
render("dodge", 0.3, lambda t, d: sfx(t, d, 270, 0.9) * 0.6)
render("parry", 0.6, lambda t, d: sfx(t, d, 1600, 0.08) * 0.6 + sfx(t, d, 2150, 0.03) * 0.2)
render("rune", 0.9, lambda t, d: sum(math.sin(t * math.tau * f) for f in (440, 660, 880)) / 4 * math.sin(t / d * math.pi) * math.exp(-t * 3))
render("death", 0.8, lambda t, d: sfx(t, d, 65, 0.65) * 0.6)
render("ambience", 16, lambda t, d: sum(math.sin(t * math.tau * f) for f in (55, 82.5, 110, 164.8125, 220)) / 20 * (0.7 + 0.3 * math.sin(t / d * math.tau)) * min(1, t, d - t))
print("Original placeholder audio generated")
