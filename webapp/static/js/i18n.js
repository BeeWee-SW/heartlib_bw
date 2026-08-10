/* Bilingual UI. Elements carry data-i18n (text) or data-i18n-attr (attributes). */

const STRINGS = {
  de: {
    "app.subtitle": "Musik aus Text · HeartMuLa",
    "lang.label": "Sprache wählen",

    "status.checking": "Prüfe System …",
    "status.ready": "Bereit",
    "status.model_loaded": "Modell geladen",
    "status.setup": "Einrichtung nötig",
    "status.no_torch": "PyTorch fehlt",
    "status.no_ckpt": "Checkpoints fehlen",
    "status.busy": "Arbeitet …",
    "status.cpu": "Kein GPU erkannt",

    "setup.title": "Einrichtung",
    "setup.intro": "Bevor Songs entstehen können, brauchen wir die Modellgewichte. Die App lädt sie auf Wunsch selbst herunter.",
    "setup.torch_missing": "PyTorch und heartlib sind nicht installiert. Führe im Repo-Verzeichnis aus:",
    "setup.torch_cmd": "pip install -e .\npip install -r webapp/requirements.txt",
    "setup.components": "Benötigte Komponenten",
    "setup.present": "vorhanden",
    "setup.missing": "fehlt",
    "setup.size_unknown": "Größe unbekannt",
    "setup.source": "Quelle",
    "setup.download": "Checkpoints herunterladen",
    "setup.downloading": "Lade herunter …",
    "setup.refresh": "Erneut prüfen",
    "setup.cli_hint": "Alternativ auf der Kommandozeile:",
    "setup.free_space": "Freier Speicher",
    "setup.ready": "Alle Checkpoints sind vorhanden.",

    "style.title": "Style",
    "style.hint": "Beschreibe den Klang des Songs",
    "style.label": "Style-Beschreibung",
    "style.placeholder": "z. B. synthwave,nostalgic,synthesizer,mid tempo,male vocals",
    "style.note": "Das Modell erwartet komma-getrennte Schlagworte. Leerzeichen um die Kommas werden automatisch entfernt. Das Feld ist freier Text — die Vorschläge sind nur eine Starthilfe.",
    "style.preview": "So wird es an das Modell übergeben",
    "style.clear": "Leeren",
    "style.count": "{n} Schlagworte",

    "group.genre": "Genre",
    "group.mood": "Stimmung",
    "group.instruments": "Instrumente",
    "group.tempo": "Tempo",
    "group.vocals": "Gesang",
    "group.production": "Produktion",

    "lyrics.title": "Lyrics",
    "lyrics.hint": "Songtext mit Struktur-Notizen",
    "lyrics.label": "Songtext",
    "lyrics.placeholder": "[Verse]\nDeine erste Zeile …\n\n[Chorus]\nDer Refrain …",
    "lyrics.markers": "Struktur einfügen",
    "lyrics.note": "Notizen in eckigen Klammern gliedern den Song. Sie steuern den Aufbau und werden nicht als Text mitgesungen.",
    "lyrics.chars": "{n} Zeichen",
    "lyrics.tokens": "≈ {n} Tokens",
    "lyrics.unbalanced_brackets": "Ungleiche Anzahl eckiger Klammern",
    "lyrics.unknown_marker": "Unbekannter Struktur-Marker — kann trotzdem funktionieren",
    "lyrics.clear": "Leeren",
    "lyrics.example": "Beispiel laden",

    "settings.title": "Einstellungen",
    "settings.hint": "Regler statt Kommandozeile",

    "p.duration": "Songlänge",
    "p.duration.desc": "Obergrenze. Das Modell darf früher enden, wenn der Song zu Ende ist.",
    "p.temperature": "Kreativität",
    "p.temperature.desc": "Niedrig klingt vorhersehbar und sauber, hoch überraschender und riskanter.",
    "p.topk": "Auswahlbreite (Top-K)",
    "p.topk.desc": "Wie viele Klangmöglichkeiten pro Schritt in Frage kommen.",
    "p.cfg": "Style-Treue",
    "p.cfg.desc": "Wie streng sich das Modell an Style und Text hält. 1.0 schaltet die Führung ab und ist etwa doppelt so schnell.",
    "p.seed": "Seed",
    "p.seed.desc": "Gleicher Seed und gleiche Einstellungen ergeben denselben Song.",
    "p.seed.placeholder": "leer = zufällig",
    "p.seed.random": "Zufälliger Seed",
    "p.seed.lock": "Seed festhalten",
    "p.seed.lock.desc": "Übernimmt den zuletzt genutzten Seed für den nächsten Lauf",
    "p.num_steps": "Decoder-Schritte",
    "p.num_steps.desc": "Mehr Schritte klingen sauberer und dauern länger.",
    "p.codec_guidance": "Decoder-Führung",
    "p.codec_guidance.desc": "Wie stark der Audio-Decoder den Klangvorgaben folgt.",
    "p.format": "Ausgabeformat",
    "p.title": "Titel",
    "p.title.placeholder": "optional",

    "advanced.title": "Experten-Einstellungen",
    "advanced.note": "Diese Werte gibt das CLI nicht her — sie steuern den Audio-Decoder direkt.",
    "advanced.devices": "Geräte und Genauigkeit werden beim Start gesetzt (siehe --mula_device, --mula_dtype).",

    "generate": "Song erzeugen",
    "generate.busy": "Erzeuge …",
    "generate.cancel": "Abbrechen",
    "generate.blocked": "Erst Einrichtung abschließen",

    "stage.load_model": "Modell laden",
    "stage.generate": "Komponieren",
    "stage.decode": "Audio decodieren",
    "stage.save": "Speichern",
    "stage.download": "Download",
    "progress.elapsed": "vergangen",
    "progress.eta": "verbleibend",
    "progress.frames": "Frames",
    "progress.hint": "Die Erzeugung läuft ungefähr in Echtzeit — ein 2-Minuten-Song braucht also etwa 2 Minuten.",

    "result.title": "Ergebnis",
    "result.download": "Herunterladen",
    "result.seed_used": "Verwendeter Seed",
    "result.time": "Rechenzeit",

    "history.title": "Historie",
    "history.hint": "Alle erzeugten Songs dieser Installation",
    "history.empty": "Noch keine Songs erzeugt.",
    "history.reuse": "Einstellungen übernehmen",
    "history.delete": "Löschen",
    "history.confirm": "Diesen Song samt Audiodatei löschen?",
    "history.reused": "Einstellungen übernommen.",

    "error.internal": "Unerwarteter Fehler",
    "error.busy": "Es läuft bereits ein Auftrag.",
    "error.tags_empty": "Bitte eine Style-Beschreibung eingeben.",
    "error.lyrics_empty": "Bitte einen Songtext eingeben.",
    "error.tags_too_long": "Die Style-Beschreibung ist zu lang. Maximal {max} Zeichen.",
    "error.lyrics_too_long": "Der Songtext ist zu lang. Maximal {max} Zeichen.",
    "error.checkpoints_missing": "Die Modell-Checkpoints fehlen noch.",
    "error.heartlib_missing": "PyTorch bzw. heartlib ist nicht installiert.",
    "error.duration_exceeds_context": "Der Songtext ist zu lang für diese Songlänge. Maximal {max} Sekunden.",
    "error.job_not_found": "Auftrag nicht gefunden.",
    "error.job_not_cancellable": "Auftrag lässt sich nicht mehr abbrechen.",
    "error.network": "Server nicht erreichbar.",
    "error.cancelled": "Auftrag abgebrochen.",
    "ok.download_done": "Checkpoints vollständig heruntergeladen.",
    "ok.generated": "Song fertig.",
    "ok.copied": "In die Zwischenablage kopiert.",

    "unit.seconds": "s",
    "unit.minutes": "min",
  },

  en: {
    "app.subtitle": "Music from text · HeartMuLa",
    "lang.label": "Choose language",

    "status.checking": "Checking system …",
    "status.ready": "Ready",
    "status.model_loaded": "Model loaded",
    "status.setup": "Setup required",
    "status.no_torch": "PyTorch missing",
    "status.no_ckpt": "Checkpoints missing",
    "status.busy": "Working …",
    "status.cpu": "No GPU detected",

    "setup.title": "Setup",
    "setup.intro": "Before any song can be made we need the model weights. The app can download them for you.",
    "setup.torch_missing": "PyTorch and heartlib are not installed. Run this in the repository root:",
    "setup.torch_cmd": "pip install -e .\npip install -r webapp/requirements.txt",
    "setup.components": "Required components",
    "setup.present": "present",
    "setup.missing": "missing",
    "setup.size_unknown": "size unknown",
    "setup.source": "Source",
    "setup.download": "Download checkpoints",
    "setup.downloading": "Downloading …",
    "setup.refresh": "Check again",
    "setup.cli_hint": "Or on the command line:",
    "setup.free_space": "Free disk space",
    "setup.ready": "All checkpoints are in place.",

    "style.title": "Style",
    "style.hint": "Describe how the song should sound",
    "style.label": "Style description",
    "style.placeholder": "e.g. synthwave,nostalgic,synthesizer,mid tempo,male vocals",
    "style.note": "The model expects comma-separated keywords. Spaces around commas are removed automatically. The field is free text — the suggestions are only a starting point.",
    "style.preview": "This is what the model receives",
    "style.clear": "Clear",
    "style.count": "{n} keywords",

    "group.genre": "Genre",
    "group.mood": "Mood",
    "group.instruments": "Instruments",
    "group.tempo": "Tempo",
    "group.vocals": "Vocals",
    "group.production": "Production",

    "lyrics.title": "Lyrics",
    "lyrics.hint": "Song text with structure notes",
    "lyrics.label": "Song text",
    "lyrics.placeholder": "[Verse]\nYour first line …\n\n[Chorus]\nThe hook …",
    "lyrics.markers": "Insert structure",
    "lyrics.note": "Notes in square brackets shape the arrangement. They guide the song rather than being sung out loud.",
    "lyrics.chars": "{n} characters",
    "lyrics.tokens": "≈ {n} tokens",
    "lyrics.unbalanced_brackets": "Unbalanced square brackets",
    "lyrics.unknown_marker": "Unknown structure marker — may still work",
    "lyrics.clear": "Clear",
    "lyrics.example": "Load example",

    "settings.title": "Settings",
    "settings.hint": "Sliders instead of command-line flags",

    "p.duration": "Song length",
    "p.duration.desc": "An upper bound. The model may stop earlier when the song is over.",
    "p.temperature": "Creativity",
    "p.temperature.desc": "Low sounds predictable and clean, high is more surprising and riskier.",
    "p.topk": "Choice width (top-k)",
    "p.topk.desc": "How many sound options are considered at each step.",
    "p.cfg": "Style adherence",
    "p.cfg.desc": "How closely the model follows style and lyrics. 1.0 turns guidance off and runs roughly twice as fast.",
    "p.seed": "Seed",
    "p.seed.desc": "The same seed with the same settings produces the same song.",
    "p.seed.placeholder": "empty = random",
    "p.seed.random": "Random seed",
    "p.seed.lock": "Keep seed",
    "p.seed.lock.desc": "Reuses the last seed for the next run",
    "p.num_steps": "Decoder steps",
    "p.num_steps.desc": "More steps sound cleaner and take longer.",
    "p.codec_guidance": "Decoder guidance",
    "p.codec_guidance.desc": "How strongly the audio decoder follows the sound target.",
    "p.format": "Output format",
    "p.title": "Title",
    "p.title.placeholder": "optional",

    "advanced.title": "Expert settings",
    "advanced.note": "The CLI does not expose these — they control the audio decoder directly.",
    "advanced.devices": "Devices and precision are set at startup (see --mula_device, --mula_dtype).",

    "generate": "Generate song",
    "generate.busy": "Generating …",
    "generate.cancel": "Cancel",
    "generate.blocked": "Finish setup first",

    "stage.load_model": "Load model",
    "stage.generate": "Compose",
    "stage.decode": "Decode audio",
    "stage.save": "Save",
    "stage.download": "Download",
    "progress.elapsed": "elapsed",
    "progress.eta": "remaining",
    "progress.frames": "frames",
    "progress.hint": "Generation runs at roughly real time — a 2-minute song takes about 2 minutes.",

    "result.title": "Result",
    "result.download": "Download",
    "result.seed_used": "Seed used",
    "result.time": "Compute time",

    "history.title": "History",
    "history.hint": "Every song this installation has made",
    "history.empty": "No songs generated yet.",
    "history.reuse": "Reuse settings",
    "history.delete": "Delete",
    "history.confirm": "Delete this song and its audio file?",
    "history.reused": "Settings applied.",

    "error.internal": "Unexpected error",
    "error.busy": "Another job is already running.",
    "error.tags_empty": "Please enter a style description.",
    "error.lyrics_empty": "Please enter song lyrics.",
    "error.tags_too_long": "The style description is too long. Maximum {max} characters.",
    "error.lyrics_too_long": "The lyrics are too long. Maximum {max} characters.",
    "error.checkpoints_missing": "The model checkpoints are still missing.",
    "error.heartlib_missing": "PyTorch or heartlib is not installed.",
    "error.duration_exceeds_context": "The lyrics are too long for this song length. Maximum {max} seconds.",
    "error.job_not_found": "Job not found.",
    "error.job_not_cancellable": "This job can no longer be cancelled.",
    "error.network": "Server unreachable.",
    "error.cancelled": "Job cancelled.",
    "ok.download_done": "Checkpoints downloaded.",
    "ok.generated": "Song ready.",
    "ok.copied": "Copied to clipboard.",

    "unit.seconds": "s",
    "unit.minutes": "min",
  },
};

const I18N = {
  lang: "de",

  init() {
    const stored = localStorage.getItem("heartmula.lang");
    if (stored && STRINGS[stored]) {
      this.lang = stored;
    } else {
      this.lang = (navigator.language || "en").toLowerCase().startsWith("de") ? "de" : "en";
    }
    document.documentElement.lang = this.lang;
    return this.lang;
  },

  set(lang) {
    this.lang = STRINGS[lang] ? lang : "en";
    localStorage.setItem("heartmula.lang", this.lang);
    document.documentElement.lang = this.lang;
    this.apply();
    // Only an actual switch fires the event — apply() alone is also used to
    // translate newly built markup, which is not a language change.
    document.dispatchEvent(new CustomEvent("i18n:changed", { detail: this.lang }));
  },

  /** Translate a key, filling {placeholders} from `vars`. */
  t(key, vars) {
    const table = STRINGS[this.lang] || STRINGS.en;
    let value = table[key] ?? STRINGS.en[key] ?? key;
    if (vars) {
      for (const [name, replacement] of Object.entries(vars)) {
        value = value.replaceAll(`{${name}}`, String(replacement));
      }
    }
    return value;
  },

  /** Re-render every translatable node in place. */
  apply(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = this.t(node.dataset.i18n);
    });
    root.querySelectorAll("[data-i18n-attr]").forEach((node) => {
      // Format: "placeholder:style.placeholder;title:style.hint"
      node.dataset.i18nAttr.split(";").forEach((pair) => {
        const [attr, key] = pair.split(":");
        if (attr && key) node.setAttribute(attr.trim(), this.t(key.trim()));
      });
    });
  },
};

export { I18N, STRINGS };
