"""Style-tag helpers, lyric structure markers and example content.

The upstream model documents no fixed tag vocabulary (README.md points at
issue #17, which is unanswered), so the chip catalogue below is a curated
starting point.  The style field itself stays free text.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import REPO_ROOT

# Section markers the model was trained on, per README.md and assets/lyrics.txt.
STRUCTURE_MARKERS = [
    "Intro",
    "Verse",
    "Prechorus",
    "Chorus",
    "Refrain",
    "Bridge",
    "Instrumental",
    "Solo",
    "Breakdown",
    "Outro",
]

# Curated suggestions, grouped for the chip rows in the UI.
TAG_GROUPS = [
    {
        "id": "genre",
        "tags": [
            "pop", "rock", "indie", "folk", "country", "hip hop", "rap", "r&b",
            "soul", "funk", "jazz", "blues", "metal", "punk", "electronic",
            "house", "techno", "synthwave", "lo-fi", "ambient", "classical",
            "orchestral", "reggae", "latin", "k-pop", "schlager",
        ],
    },
    {
        "id": "mood",
        "tags": [
            "happy", "sad", "melancholic", "energetic", "calm", "dreamy",
            "dark", "epic", "romantic", "nostalgic", "uplifting", "aggressive",
            "chill", "hopeful", "mysterious", "playful",
        ],
    },
    {
        "id": "instruments",
        "tags": [
            "piano", "acoustic guitar", "electric guitar", "bass", "drums",
            "synthesizer", "strings", "violin", "cello", "saxophone",
            "trumpet", "flute", "organ", "harp", "accordion", "808",
        ],
    },
    {
        "id": "tempo",
        "tags": [
            "slow", "mid tempo", "upbeat", "fast", "driving", "laid back",
            "60 bpm", "90 bpm", "120 bpm", "140 bpm",
        ],
    },
    {
        "id": "vocals",
        "tags": [
            "male vocals", "female vocals", "duet", "choir", "harmonies",
            "whispered", "powerful vocals", "rap verse", "instrumental",
        ],
    },
    {
        "id": "production",
        "tags": [
            "clean production", "lo-fi production", "live recording",
            "reverb", "distorted", "acoustic", "cinematic", "minimal",
            "layered", "vintage",
        ],
    },
]

# A handful of ready-made starting points shown in the "examples" menu.
EXAMPLES = [
    {
        "id": "ordinary-magic",
        "title": {"de": "Ordinary Magic (Repo-Beispiel)", "en": "Ordinary Magic (repo example)"},
        "tags": "piano,happy",
        "lyrics_file": "assets/lyrics.txt",
    },
    {
        "id": "synthwave-night",
        "title": {"de": "Synthwave Nacht", "en": "Synthwave Night"},
        "tags": "synthwave,nostalgic,synthesizer,mid tempo,male vocals,reverb",
        "lyrics": """[Intro]

[Verse]
Neon bleeding on the empty street
Engine humming to a steady beat
Every window holds a different light
I am driving out into the night

[Chorus]
Hold the line, hold the line
Everything we lost we leave behind
Hold the line, hold the line
Chasing headlights til the morning finds us

[Verse]
Radio is playing something old
Static warmer than the city cold
Mile by mile the map begins to blur
Nothing here is quite the way it were

[Chorus]
Hold the line, hold the line
Everything we lost we leave behind
Hold the line, hold the line
Chasing headlights til the morning finds us

[Outro]
Til the morning finds us
""",
    },
    {
        "id": "akustik-abschied",
        "title": {"de": "Akustischer Abschied", "en": "Acoustic Goodbye"},
        "tags": "folk,melancholic,acoustic guitar,slow,female vocals,acoustic",
        "lyrics": """[Intro]

[Verse]
Der Regen schreibt dein Namen auf das Glas
Ich zaehle Tropfen bis ich dich vergass
Die Tuer faellt zu und niemand sagt ein Wort
Der Kaffee wird kalt und du bist fort

[Refrain]
Und ich singe leise weiter
Auch wenn keiner mit mir singt
Jede Zeile eine Leiter
Bis das Morgenlicht beginnt

[Verse]
Die Strassen kennen jeden meiner Wege
Ich trage deine Jacke durch den Herbst
Und irgendwo im Rauschen dieser Tage
Ist ein Ton der mir gehoert

[Refrain]
Und ich singe leise weiter
Auch wenn keiner mit mir singt
Jede Zeile eine Leiter
Bis das Morgenlicht beginnt

[Outro]
Bis das Morgenlicht beginnt
""",
    },
]

_WHITESPACE = re.compile(r"\s+")


def normalize_tags(raw: str) -> str:
    """Turn free-form style input into the format the model expects.

    The pipeline lowercases the string and wraps it in ``<tag>…</tag>``
    (music_generation.py:205-216); the documented format is comma separated
    *without* spaces around the commas.  Spaces inside a single tag are kept,
    so ``lo-fi hip hop`` survives intact.
    """
    if not raw:
        return ""
    parts = re.split(r"[,\n;]+", raw)
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        tag = _WHITESPACE.sub(" ", part).strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return ",".join(out)


def validate_lyrics(text: str) -> list[str]:
    """Return a list of human-readable warning codes for the lyrics input."""
    warnings: list[str] = []
    if text.count("[") != text.count("]"):
        warnings.append("lyrics.unbalanced_brackets")
    known = {m.lower() for m in STRUCTURE_MARKERS}
    for match in re.findall(r"\[([^\]\n]*)\]", text):
        label = match.strip().lower()
        if label and label not in known:
            warnings.append("lyrics.unknown_marker")
            break
    return warnings


def load_example(example_id: str) -> dict | None:
    """Resolve one example, reading its lyrics file if it references one."""
    for example in EXAMPLES:
        if example["id"] != example_id:
            continue
        result = {"id": example["id"], "title": example["title"], "tags": example["tags"]}
        if "lyrics" in example:
            result["lyrics"] = example["lyrics"]
        else:
            path = Path(REPO_ROOT / example["lyrics_file"])
            result["lyrics"] = path.read_text(encoding="utf-8") if path.is_file() else ""
        return result
    return None
