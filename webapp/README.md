# HeartMuLa Studio

A local web UI for the HeartMuLa music generation model — style tags, lyrics with
structure markers, and every generation setting behind a slider or a switch.
Bilingual (DE/EN), dark theme, no build step, no CDN.

*Deutsche Fassung weiter unten.*

---

## English

### 1. Install

```bash
git clone <this repo> && cd heartlib_bw
pip install -e .                        # the model library
pip install -r webapp/requirements.txt  # the web layer
```

Python 3.10 is what upstream recommends. A CUDA GPU is required for actual
generation — see *Hardware* below.

### 2. Start

```bash
python -m webapp.main --open
```

The server comes up at <http://127.0.0.1:8000>. It starts **even without
PyTorch, without a GPU and without checkpoints** — in that case the page shows a
setup screen instead of crashing.

### 3. Get the checkpoints

Open the app and use **Download checkpoints** in the setup card. It fetches
three components (~10 GB in total) from Hugging Face, falling back to ModelScope
if the hub is unreachable, and resumes interrupted downloads:

| Component | Repository | Lands in |
|---|---|---|
| Tokenizer & generation config | `HeartMuLa/HeartMuLaGen` | `ckpt/` |
| HeartMuLa 3B (language model) | `HeartMuLa/HeartMuLa-oss-3B-happy-new-year` | `ckpt/HeartMuLa-oss-3B/` |
| HeartCodec (audio decoder) | `HeartMuLa/HeartCodec-oss-20260123` | `ckpt/HeartCodec-oss/` |

The same card prints the equivalent `hf download` / `modelscope download`
commands if you would rather run them yourself.

### 4. Make a song

1. **Style** — comma-separated keywords describing the sound
   (`synthwave,nostalgic,synthesizer,mid tempo,male vocals`). Click the chips or
   type freely; the app normalises spacing, case and duplicates before handing
   the string to the model. The preview box shows exactly what gets sent.
2. **Lyrics** — the song text. Bracketed notes such as `[Verse]`, `[Chorus]` or
   `[Refrain]` shape the arrangement; the buttons above the textarea insert them
   at the cursor.
3. Adjust the sliders, press **Generate song**.

Generation runs at roughly real time: a two-minute song takes about two minutes,
plus vocoder decoding. Progress, elapsed time and an estimate are shown live,
and the run can be cancelled.

### Settings

| Control | Model parameter | Range | Default |
|---|---|---|---|
| Song length | `max_audio_length_ms` | 15–300 s | 120 s |
| Creativity | `temperature` | 0.1–2.0 | 1.0 |
| Choice width | `topk` | 1–200 | 50 |
| Style adherence | `cfg_scale` | 1.0–3.0 | 1.5 |
| Seed | *(added by this app)* | 0–2³²−1 or empty | random |
| Decoder steps | `num_steps` | 5–50 | 10 |
| Decoder guidance | `guidance_scale` | 1.0–3.0 | 1.25 |
| Output format | — | wav / flac / mp3 | wav |

`cfg_scale = 1.0` switches classifier-free guidance off and runs roughly twice
as fast, because the model no longer needs a second batch entry. The decoder
settings are not available through the upstream CLI at all.

**Reproducibility.** The library has no seed of its own, so the app seeds both
the language model and the vocoder's flow-matching noise. Identical settings on
identical hardware and dtype give an identical file; across different GPUs, CUDA
kernels may still differ.

MP3 output is only offered when `torchaudio` finds an ffmpeg backend. WAV is the
default and always works — expect roughly 11 MB per minute of stereo audio.

### Command-line options

```
--model_path PATH     checkpoint root (default ./ckpt)
--output_dir PATH     where songs are written (default ./outputs)
--version 3B          HeartMuLa version folder suffix
--mula_device cuda    device for the language model, e.g. cuda:0
--codec_device cuda   device for the vocoder, e.g. cuda:1
--mula_dtype bf16     bf16 | fp16 | fp32
--codec_dtype fp32    bf16 degrades audio quality here
--lazy_load           load and free modules on demand to save VRAM
--host / --port       bind address (default 127.0.0.1:8000)
--hf_endpoint URL     alternative Hugging Face mirror
--open                open a browser on start
```

### Hardware

Roughly 8–10 GB of VRAM for the 3B model in bf16 plus the fp32 decoder; a
`cfg_scale` above 1.0 doubles the language model's batch. Two GPUs can be split
with `--mula_device cuda:0 --codec_device cuda:1` (which disables `--lazy_load`,
as upstream does). On a single card, `--lazy_load` frees each module after use.
There is no supported CPU or MPS path.

### Notes and limits

- **One job at a time.** The pipeline mutates shared KV caches, so requests are
  serialised through a single worker. A second generation is refused with a
  clear message rather than corrupting the first.
- **Reference audio** is wired into the model but raises `NotImplementedError`
  upstream, so the app does not offer it.
- **Tag vocabulary.** Upstream documents none (issue #17 is unanswered), so the
  chips are a curated suggestion list, not a fixed vocabulary. The field stays
  free text.
- **History** lives in `outputs/history.json` next to the audio files. Deleting
  an entry removes its file too.

### Files

```
webapp/
├── main.py          CLI entry point
├── config.py        paths, devices, constants
├── routes.py        FastAPI endpoints
├── engine.py        model manager, pipeline subclass, generation
├── jobs.py          single-worker queue with cancellation
├── progress.py      progress reporting for a library without callbacks
├── checkpoints.py   detection and download
├── presets.py       tag normalisation, structure markers, examples
├── schemas.py       request validation and parameter ranges
└── static/          index.html, css/style.css, js/{app,api,i18n}.js
```

`src/heartlib/` is untouched: the app subclasses `HeartMuLaGenPipeline` and
temporarily swaps the module-level `tqdm` symbol instead of patching the
library, so the upstream repository stays cleanly rebaseable.

---

## Deutsch

### 1. Installation

```bash
git clone <dieses Repo> && cd heartlib_bw
pip install -e .                        # die Modell-Bibliothek
pip install -r webapp/requirements.txt  # die Web-Schicht
```

Upstream empfiehlt Python 3.10. Für die eigentliche Erzeugung wird eine
CUDA-GPU benötigt (siehe *Hardware*).

### 2. Start

```bash
python -m webapp.main --open
```

Der Server läuft auf <http://127.0.0.1:8000> und startet **auch ohne PyTorch,
ohne GPU und ohne Checkpoints** — dann zeigt die Seite eine Einrichtungs-Karte
statt eines Fehlers.

### 3. Checkpoints holen

In der Einrichtungs-Karte auf **Checkpoints herunterladen** klicken. Die App
lädt drei Komponenten (zusammen rund 10 GB) von Hugging Face, weicht bei
Problemen auf ModelScope aus und setzt abgebrochene Downloads fort:

| Komponente | Repository | Ziel |
|---|---|---|
| Tokenizer & Generierungs-Konfiguration | `HeartMuLa/HeartMuLaGen` | `ckpt/` |
| HeartMuLa 3B (Sprachmodell) | `HeartMuLa/HeartMuLa-oss-3B-happy-new-year` | `ckpt/HeartMuLa-oss-3B/` |
| HeartCodec (Audio-Decoder) | `HeartMuLa/HeartCodec-oss-20260123` | `ckpt/HeartCodec-oss/` |

Dieselbe Karte zeigt die passenden `hf download`- bzw. `modelscope
download`-Befehle zum Kopieren.

### 4. Song erzeugen

1. **Style** — komma-getrennte Schlagworte, die den Klang beschreiben
   (`synthwave,nostalgic,synthesizer,mid tempo,male vocals`). Chips anklicken
   oder frei tippen; die App vereinheitlicht Groß-/Kleinschreibung, Leerzeichen
   und Doppelungen, bevor der Text an das Modell geht. Die Vorschau zeigt genau,
   was gesendet wird.
2. **Lyrics** — der Songtext. Notizen in eckigen Klammern wie `[Verse]`,
   `[Chorus]` oder `[Refrain]` gliedern den Aufbau; die Buttons über dem Textfeld
   fügen sie an der Cursorposition ein.
3. Regler einstellen, **Song erzeugen** drücken.

Die Erzeugung läuft ungefähr in Echtzeit: ein Zwei-Minuten-Song braucht etwa
zwei Minuten, dazu kommt die Decodierung. Fortschritt, verstrichene Zeit und
eine Schätzung sind live sichtbar, der Lauf lässt sich abbrechen.

### Einstellungen

| Regler | Modell-Parameter | Bereich | Standard |
|---|---|---|---|
| Songlänge | `max_audio_length_ms` | 15–300 s | 120 s |
| Kreativität | `temperature` | 0,1–2,0 | 1,0 |
| Auswahlbreite | `topk` | 1–200 | 50 |
| Style-Treue | `cfg_scale` | 1,0–3,0 | 1,5 |
| Seed | *(von dieser App ergänzt)* | 0–2³²−1 oder leer | zufällig |
| Decoder-Schritte | `num_steps` | 5–50 | 10 |
| Decoder-Führung | `guidance_scale` | 1,0–3,0 | 1,25 |
| Ausgabeformat | — | wav / flac / mp3 | wav |

`cfg_scale = 1.0` schaltet die Classifier-Free-Guidance ab und ist etwa doppelt
so schnell, weil das Modell keinen zweiten Batch-Eintrag mehr braucht. Die
Decoder-Regler bietet das Upstream-CLI überhaupt nicht an.

**Reproduzierbarkeit.** Die Bibliothek kennt keinen Seed, deshalb setzt die App
ihn selbst — sowohl für das Sprachmodell als auch für das Rauschen des
Vokoders. Gleiche Einstellungen auf gleicher Hardware und mit gleichem dtype
ergeben dieselbe Datei; über verschiedene GPUs hinweg können CUDA-Kernel
abweichen.

MP3 wird nur angeboten, wenn `torchaudio` ein ffmpeg-Backend findet. WAV ist der
Standard und funktioniert immer — rund 11 MB pro Minute Stereo.

### Kommandozeilen-Optionen

```
--model_path PFAD     Checkpoint-Wurzel (Standard ./ckpt)
--output_dir PFAD     Ablage der Songs (Standard ./outputs)
--version 3B          Versions-Suffix des HeartMuLa-Ordners
--mula_device cuda    Gerät für das Sprachmodell, z. B. cuda:0
--codec_device cuda   Gerät für den Vokoder, z. B. cuda:1
--mula_dtype bf16     bf16 | fp16 | fp32
--codec_dtype fp32    bf16 mindert hier die Audioqualität
--lazy_load           Module bei Bedarf laden und wieder freigeben (spart VRAM)
--host / --port       Bind-Adresse (Standard 127.0.0.1:8000)
--hf_endpoint URL     alternativer Hugging-Face-Spiegel
--open                Browser beim Start öffnen
```

### Hardware

Etwa 8–10 GB VRAM für das 3B-Modell in bf16 plus den fp32-Decoder; ein
`cfg_scale` über 1,0 verdoppelt den Batch des Sprachmodells. Zwei GPUs lassen
sich mit `--mula_device cuda:0 --codec_device cuda:1` aufteilen (das schaltet
`--lazy_load` ab, genau wie Upstream). Auf einer einzelnen Karte gibt
`--lazy_load` jedes Modul nach Gebrauch wieder frei. Einen unterstützten CPU-
oder MPS-Pfad gibt es nicht.

### Hinweise und Grenzen

- **Ein Auftrag zur Zeit.** Die Pipeline verändert geteilte KV-Caches, deshalb
  laufen Anfragen über genau einen Worker. Eine zweite Generierung wird mit
  einer klaren Meldung abgelehnt, statt die erste zu beschädigen.
- **Referenz-Audio** ist im Modell vorgesehen, wirft Upstream aber
  `NotImplementedError` — die App bietet es daher nicht an.
- **Tag-Vokabular.** Upstream dokumentiert keines (Issue #17 ist unbeantwortet),
  die Chips sind also eine kuratierte Vorschlagsliste, kein festes Vokabular.
  Das Feld bleibt freier Text.
- **Historie** liegt als `outputs/history.json` neben den Audiodateien. Beim
  Löschen eines Eintrags verschwindet auch die Datei.

### Dateien

```
webapp/
├── main.py          Einstiegspunkt für die Kommandozeile
├── config.py        Pfade, Geräte, Konstanten
├── routes.py        FastAPI-Endpunkte
├── engine.py        Modell-Manager, Pipeline-Subklasse, Generierung
├── jobs.py          Single-Worker-Queue mit Abbruch
├── progress.py      Fortschritt für eine Bibliothek ohne Callbacks
├── checkpoints.py   Erkennung und Download
├── presets.py       Tag-Normalisierung, Struktur-Marker, Beispiele
├── schemas.py       Validierung und Parameter-Bereiche
└── static/          index.html, css/style.css, js/{app,api,i18n}.js
```

`src/heartlib/` bleibt unangetastet: Die App leitet von `HeartMuLaGenPipeline`
ab und tauscht das `tqdm`-Symbol nur vorübergehend aus, statt die Bibliothek zu
verändern — so bleibt das Upstream-Repo sauber rebasebar.
