"""OPTIONAL (off by default; set ENABLE_VIDEO=1): ElevenLabs text-to-speech + an ffmpeg slideshow.
Needs: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID_EN / _HI, ffmpeg + ffprobe on PATH, and `pip install matplotlib`.
Not exercised by the test-suite (needs network, ffmpeg and a paid API); run it manually first."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

from . import config, history
from . import indicators as ind


def tts(text: str, voice_id: str, api_key: str, out: Path, model: str = "eleven_multilingual_v2") -> Path:
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}", method="POST",
        data=json.dumps({"text": text, "model_id": model}).encode(),
        headers={"xi-api-key": api_key, "content-type": "application/json", "accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out.write_bytes(r.read())
    return out


def _slides(settings: config.Settings, post: dict, lang: str, folder: Path) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import compliance as comp
    c, paths = post[lang], []

    def text_slide(name, heading, body):
        fig = plt.figure(figsize=(12.8, 7.2), facecolor="#12151c")
        fig.text(0.05, 0.85, heading, color="white", fontsize=30, weight="bold", wrap=True, va="top")
        fig.text(0.05, 0.65, body, color="#c9d1e0", fontsize=20, wrap=True, va="top")
        p = folder / f"{name}.png"
        fig.savefig(p, dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        paths.append(p)

    text_slide("s0", c["title"], "\n".join(c["summary"]))
    for key, v in post["facts"]["indices"].items():
        series = history.load_series(settings, key, upto=post["date"])[-252:]
        if len(series) < 5:
            continue
        fig, ax = plt.subplots(figsize=(12.8, 7.2), facecolor="#12151c")
        ax.set_facecolor("#12151c")
        closes = [s["c"] for s in series]
        ax.plot(range(len(closes)), closes, color="#6aa5ff", lw=2)
        ax.plot(range(len(closes)), [x if x else float("nan") for x in ind.sma_series(closes, 50)], color="#ffb454", ls="--")
        ax.set_title(f"{v['name']}  {v['last']:,.2f}  ({v['change_pct']:+.2f}%)", color="white", fontsize=26)
        ax.tick_params(colors="#9aa3b5")
        p = folder / f"{key}.png"
        fig.savefig(p, dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        paths.append(p)
    text_slide("s_end", "Disclaimer" if lang == "en" else "अस्वीकरण", comp.DISCLAIMER[lang])
    return paths


def render(settings: config.Settings, post: dict, lang: str, script_text: str) -> Path | None:
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    voice = os.environ.get(f"ELEVENLABS_VOICE_ID_{lang.upper()}", "")
    if not (key and voice and shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("WARN: video skipped (need ELEVENLABS_API_KEY, voice id, ffmpeg)")
        return None
    folder = settings.posts_dir / post["date"] / "video" / lang
    folder.mkdir(parents=True, exist_ok=True)
    audio = tts(script_text, voice, key, folder / "voice.mp3")
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                         "-of", "default=nw=1:nk=1", str(audio)]).strip())
    slides = _slides(settings, post, lang, folder)
    per = dur / len(slides)
    listing = folder / "slides.txt"
    listing.write_text("".join(f"file '{p.name}'\nduration {per:.3f}\n" for p in slides) + f"file '{slides[-1].name}'\n")
    out = folder / f"market_{post['date']}_{lang}.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-i", str(audio), "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-shortest", str(out)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out
