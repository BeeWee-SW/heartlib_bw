import { I18N } from "./i18n.js";
import { API, ApiError, followJob } from "./api.js";

const $ = (id) => document.getElementById(id);

const state = {
  status: null,
  presets: null,
  lastSeed: null,
  activeJob: null,
  params: {},
};

/* Sliders shown in the main panel and behind the expert toggle. Each maps
   straight onto a request field so the UI cannot invent parameters. */
const MAIN_SLIDERS = [
  { key: "duration_s", labelKey: "p.duration", descKey: "p.duration.desc", format: formatDuration },
  { key: "temperature", labelKey: "p.temperature", descKey: "p.temperature.desc", decimals: 2 },
  { key: "topk", labelKey: "p.topk", descKey: "p.topk.desc" },
  { key: "cfg_scale", labelKey: "p.cfg", descKey: "p.cfg.desc", decimals: 1 },
];

const ADVANCED_SLIDERS = [
  { key: "num_steps", labelKey: "p.num_steps", descKey: "p.num_steps.desc" },
  { key: "codec_guidance_scale", labelKey: "p.codec_guidance", descKey: "p.codec_guidance.desc", decimals: 2 },
];

const STAGES = ["load_model", "generate", "decode", "save"];

/* ------------------------------------------------------------- helpers */
function formatDuration(seconds) {
  const value = Number(seconds);
  if (value < 60) return `${value} ${I18N.t("unit.seconds")}`;
  const minutes = Math.floor(value / 60);
  const rest = value % 60;
  return rest ? `${minutes}:${String(rest).padStart(2, "0")} ${I18N.t("unit.minutes")}` : `${minutes} ${I18N.t("unit.minutes")}`;
}

function formatBytes(bytes) {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function formatSeconds(seconds) {
  if (seconds == null) return "—";
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  return minutes ? `${minutes}:${String(total % 60).padStart(2, "0")}` : `${total}s`;
}

function toast(message, kind = "") {
  const node = document.createElement("div");
  node.className = `toast${kind ? ` toast--${kind}` : ""}`;
  node.textContent = message;
  $("toasts").appendChild(node);
  setTimeout(() => node.remove(), 5200);
}

function toastError(err) {
  if (err instanceof ApiError) {
    const payload = err.payload || {};
    const vars = { max: payload.max_duration_s ?? payload.max };
    toast(I18N.t(err.code, vars), err.code === "error.cancelled" ? "" : "error");
  } else {
    toast(String(err && err.message ? err.message : err), "error");
  }
}

/* ------------------------------------------------------------- sliders */
function buildSlider(spec, ranges, defaults) {
  const range = ranges[spec.key] || { min: 0, max: 1, step: 0.1 };
  const wrapper = document.createElement("div");
  wrapper.className = "slider";
  wrapper.innerHTML = `
    <div class="slider__top">
      <span class="slider__name" data-i18n="${spec.labelKey}"></span>
      <span class="slider__value"></span>
    </div>
    <input type="range" min="${range.min}" max="${range.max}" step="${range.step}">
    <span class="slider__desc" data-i18n="${spec.descKey}"></span>`;

  const input = wrapper.querySelector("input");
  const value = wrapper.querySelector(".slider__value");
  input.value = defaults[spec.key];
  state.params[spec.key] = Number(defaults[spec.key]);

  const render = () => {
    const numeric = Number(input.value);
    state.params[spec.key] = numeric;
    value.textContent = spec.format
      ? spec.format(numeric)
      : spec.decimals
        ? numeric.toFixed(spec.decimals)
        : String(numeric);
    const percent = ((numeric - range.min) / (range.max - range.min)) * 100;
    input.style.setProperty("--fill", `${percent}%`);
  };

  input.addEventListener("input", render);
  document.addEventListener("i18n:changed", render);
  render();
  return wrapper;
}

/* ---------------------------------------------------------------- tags */
function currentTags() {
  return $("tags").value
    .split(/[,\n;]+/)
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
}

function setTags(list) {
  $("tags").value = list.join(",");
  refreshTags();
}

function toggleTag(tag) {
  const list = currentTags();
  const index = list.indexOf(tag.toLowerCase());
  if (index >= 0) list.splice(index, 1);
  else list.push(tag.toLowerCase());
  setTags(list);
}

let tagTimer = null;
function refreshTags() {
  const active = new Set(currentTags());
  document.querySelectorAll(".chip[data-tag]").forEach((chip) => {
    chip.setAttribute("aria-pressed", active.has(chip.dataset.tag.toLowerCase()) ? "true" : "false");
  });
  clearTimeout(tagTimer);
  tagTimer = setTimeout(async () => {
    try {
      const result = await API.previewTags($("tags").value);
      $("tag-preview").textContent = result.normalized;
      $("tag-count").textContent = result.count ? I18N.t("style.count", { n: result.count }) : "";
    } catch {
      /* preview is cosmetic */
    }
  }, 180);
}

/* -------------------------------------------------------------- lyrics */
function insertMarker(marker) {
  const area = $("lyrics");
  const start = area.selectionStart ?? area.value.length;
  const end = area.selectionEnd ?? start;
  const before = area.value.slice(0, start);
  const after = area.value.slice(end);
  // Keep markers on their own line — that is how the training data looks.
  const prefix = before && !before.endsWith("\n") ? "\n" : "";
  const snippet = `${prefix}[${marker}]\n`;
  area.value = before + snippet + after;
  const caret = (before + snippet).length;
  area.focus();
  area.setSelectionRange(caret, caret);
  refreshLyrics();
}

let lyricsTimer = null;
function refreshLyrics() {
  clearTimeout(lyricsTimer);
  lyricsTimer = setTimeout(async () => {
    try {
      const result = await API.checkLyrics($("lyrics").value);
      $("lyrics-chars").textContent = I18N.t("lyrics.chars", { n: result.characters });
      $("lyrics-tokens").textContent = I18N.t("lyrics.tokens", { n: result.estimated_tokens });
      $("lyrics-warn").textContent = result.warnings.map((w) => I18N.t(w)).join(" · ");
    } catch {
      /* validation is advisory */
    }
  }, 220);
}

/* -------------------------------------------------------------- status */
function renderStatus(status) {
  state.status = status;
  const dot = $("status-dot");
  const text = $("status-text");
  dot.className = "dot";

  if (!status.torch.installed || !status.heartlib_installed) {
    dot.classList.add("dot--err");
    text.textContent = I18N.t("status.no_torch");
  } else if (!status.checkpoints.ready) {
    dot.classList.add("dot--warn");
    text.textContent = I18N.t("status.no_ckpt");
  } else if (status.model.loaded) {
    dot.classList.add("dot--ok");
    text.textContent = I18N.t("status.model_loaded");
  } else {
    dot.classList.add("dot--ok");
    text.textContent = I18N.t("status.ready");
  }

  const deviceChip = $("device-chip");
  if (status.torch.installed) {
    const gpu = status.torch.gpus[0];
    deviceChip.hidden = false;
    deviceChip.textContent = gpu
      ? `${gpu.name} · ${formatBytes(gpu.total_bytes)}`
      : I18N.t("status.cpu");
  } else {
    deviceChip.hidden = true;
  }

  const blocked = !status.can_generate;
  $("btn-generate").disabled = blocked || Boolean(state.activeJob);
  $("btn-generate").querySelector("span").textContent =
    blocked ? I18N.t("generate.blocked") : I18N.t("generate");

  $("setup-card").hidden = status.can_generate;
  $("setup-torch").hidden = status.torch.installed && status.heartlib_installed;
  $("setup-torch-cmd").textContent = I18N.t("setup.torch_cmd");

  const formatSelect = $("audio-format");
  if (formatSelect.options.length !== status.audio_formats.length) {
    formatSelect.innerHTML = "";
    status.audio_formats.forEach((fmt) => {
      const option = document.createElement("option");
      option.value = fmt;
      option.textContent = fmt.toUpperCase();
      formatSelect.appendChild(option);
    });
    formatSelect.value = status.audio_formats.includes(status.defaults.audio_format)
      ? status.defaults.audio_format
      : status.audio_formats[0];
  }

  $("advanced-devices").textContent =
    `${I18N.t("advanced.devices")} — mula: ${status.defaults.mula_device} · codec: ${status.defaults.codec_device}`;
}

async function renderSetup() {
  const source = $("setup-source").value;
  let plan;
  try {
    plan = await API.checkpointPlan(source);
  } catch (err) {
    toastError(err);
    return;
  }

  const list = $("setup-list");
  list.innerHTML = "";
  plan.components.forEach((component) => {
    const row = document.createElement("div");
    row.className = "setup__item";
    row.dataset.component = component.id;
    row.innerHTML = `
      <span class="dot ${component.present ? "dot--ok" : "dot--warn"}"></span>
      <span></span>
      <span class="setup__size"></span>`;
    row.querySelector("span:nth-child(2)").textContent =
      component.label[I18N.lang] || component.label.en;
    row.querySelector(".setup__size").textContent = component.present
      ? `${I18N.t("setup.present")} · ${formatBytes(component.local_bytes)}`
      : `${I18N.t("setup.missing")} · ${I18N.t("setup.size_unknown")}`;
    list.appendChild(row);
  });

  $("setup-cli").textContent = (plan.cli || []).join("\n");
  const free = document.createElement("div");
  free.className = "card__note";
  free.textContent = `${I18N.t("setup.free_space")}: ${formatBytes(plan.free_bytes)}`;
  list.appendChild(free);

  // Sizes come from the hub and may be slow or unavailable, so they are
  // filled in afterwards rather than holding up the whole card.
  API.checkpointSizes()
    .then(({ sizes }) => {
      plan.components.forEach((component) => {
        if (component.present) return;
        const bytes = (sizes[component.id] || {}).bytes;
        if (!bytes) return;
        const cell = list.querySelector(`[data-component="${component.id}"] .setup__size`);
        if (cell) cell.textContent = `${I18N.t("setup.missing")} · ${formatBytes(bytes)}`;
      });
    })
    .catch(() => {
      /* size is a nicety; the setup card works without it */
    });
}

/* ------------------------------------------------------------ progress */
function renderStages(activeStage) {
  const container = $("gen-stages");
  container.innerHTML = "";
  const activeIndex = STAGES.indexOf(activeStage);
  STAGES.forEach((stage, index) => {
    const node = document.createElement("span");
    node.className = "stage";
    if (index === activeIndex) node.classList.add("is-active");
    else if (activeIndex >= 0 && index < activeIndex) node.classList.add("is-done");
    node.textContent = I18N.t(`stage.${stage}`);
    container.appendChild(node);
  });
}

function renderJob(job) {
  $("gen-bar").style.width = `${Math.round(job.progress * 100)}%`;
  $("gen-msg").textContent = job.message
    ? `${I18N.t(`stage.${job.stage}`, {})} · ${job.message} ${I18N.t("progress.frames")}`
    : I18N.t(`stage.${job.stage}`);
  $("gen-elapsed").textContent = `${I18N.t("progress.elapsed")} ${formatSeconds(job.elapsed_s)}`;
  $("gen-eta").textContent = job.eta_s != null ? `${I18N.t("progress.eta")} ${formatSeconds(job.eta_s)}` : "";
  renderStages(job.stage);
}

function setBusy(busy) {
  const button = $("btn-generate");
  button.disabled = busy || !(state.status && state.status.can_generate);
  button.classList.toggle("is-busy", busy);
  button.querySelector("span").textContent = busy
    ? I18N.t("generate.busy")
    : state.status && state.status.can_generate
      ? I18N.t("generate")
      : I18N.t("generate.blocked");
  $("gen-progress").classList.toggle("is-active", busy);
  $("gen-hint").hidden = busy;
}

/* ------------------------------------------------------------- history */
function renderHistory(entries) {
  const container = $("history");
  container.innerHTML = "";
  if (!entries.length) {
    container.innerHTML = `<p class="empty">${I18N.t("history.empty")}</p>`;
    return;
  }
  entries.forEach((entry) => {
    const settings = entry.settings || {};
    const card = document.createElement("article");
    card.className = "song";
    card.innerHTML = `
      <div class="song__head">
        <span class="song__title"></span>
        <span class="song__time"></span>
      </div>
      <div class="song__tags"></div>
      <audio controls preload="none" src="/api/audio/${entry.id}"></audio>
      <div class="song__facts"></div>
      <div class="song__actions">
        <a class="btn btn--ghost" href="/api/audio/${entry.id}?download=true" download></a>
        <button class="btn btn--ghost" data-action="reuse" type="button"></button>
        <button class="btn btn--ghost btn--danger" data-action="delete" type="button"></button>
      </div>`;

    card.querySelector(".song__title").textContent = entry.title || entry.id;
    card.querySelector(".song__time").textContent = new Date(entry.created_at * 1000)
      .toLocaleString(I18N.lang === "de" ? "de-DE" : "en-GB", { dateStyle: "short", timeStyle: "short" });
    card.querySelector(".song__tags").textContent = settings.tags || "";
    card.querySelector(".song__facts").textContent = [
      formatDuration(settings.duration_s ?? 0),
      `seed ${settings.seed}`,
      `temp ${settings.temperature}`,
      `top-k ${settings.topk}`,
      `cfg ${settings.cfg_scale}`,
      formatBytes(entry.bytes),
      `${I18N.t("result.time")} ${formatSeconds(entry.generation_s)}`,
    ].join(" · ");

    card.querySelector("a").textContent = I18N.t("result.download");
    const reuse = card.querySelector('[data-action="reuse"]');
    const remove = card.querySelector('[data-action="delete"]');
    reuse.textContent = I18N.t("history.reuse");
    remove.textContent = I18N.t("history.delete");

    reuse.addEventListener("click", () => applySettings(settings));
    remove.addEventListener("click", async () => {
      if (!confirm(I18N.t("history.confirm"))) return;
      try {
        await API.deleteEntry(entry.id);
        await loadHistory();
      } catch (err) {
        toastError(err);
      }
    });

    container.appendChild(card);
  });
}

function applySettings(settings) {
  if (settings.tags) $("tags").value = settings.tags;
  if (settings.lyrics) $("lyrics").value = settings.lyrics;
  if (settings.seed != null) $("seed").value = settings.seed;
  document.querySelectorAll(".slider input[type=range]").forEach((input) => {
    const key = input.closest(".slider").dataset.key;
    if (key && settings[key] != null) {
      input.value = settings[key];
      input.dispatchEvent(new Event("input"));
    }
  });
  if (settings.audio_format) $("audio-format").value = settings.audio_format;
  refreshTags();
  refreshLyrics();
  window.scrollTo({ top: 0, behavior: "smooth" });
  toast(I18N.t("history.reused"), "ok");
}

async function loadHistory() {
  try {
    renderHistory((await API.history()).entries);
  } catch (err) {
    toastError(err);
  }
}

/* ------------------------------------------------------------- actions */
async function runGeneration() {
  const payload = {
    tags: $("tags").value,
    lyrics: $("lyrics").value,
    ...state.params,
    duration_s: Math.round(state.params.duration_s),
    topk: Math.round(state.params.topk),
    num_steps: Math.round(state.params.num_steps),
    audio_format: $("audio-format").value,
    title: $("song-title").value || null,
  };
  const seedField = $("seed").value.trim();
  payload.seed = seedField === "" ? null : Number(seedField);

  if (!payload.tags.trim()) return toast(I18N.t("error.tags_empty"), "error");
  if (!payload.lyrics.trim()) return toast(I18N.t("error.lyrics_empty"), "error");

  setBusy(true);
  $("result").classList.remove("is-active");
  renderStages("load_model");

  try {
    const job = await API.generate(payload);
    state.activeJob = job.id;
    const finished = await followJob(job.id, renderJob);
    showResult(finished.result);
    toast(I18N.t("ok.generated"), "ok");
    await loadHistory();
    await refreshStatus();
  } catch (err) {
    toastError(err);
  } finally {
    state.activeJob = null;
    setBusy(false);
  }
}

function showResult(entry) {
  if (!entry) return;
  state.lastSeed = entry.settings.seed;
  if ($("seed-lock").checked) $("seed").value = entry.settings.seed;

  $("result-title").textContent = entry.title;
  $("result-audio").src = `/api/audio/${entry.id}`;
  $("result-download").href = `/api/audio/${entry.id}?download=true`;
  $("result-facts").textContent = [
    `${I18N.t("result.seed_used")} ${entry.settings.seed}`,
    `${I18N.t("result.time")} ${formatSeconds(entry.generation_s)}`,
    formatBytes(entry.bytes),
  ].join(" · ");
  $("result").classList.add("is-active");
}

async function runDownload() {
  $("btn-download").disabled = true;
  $("download-progress").classList.add("is-active");
  try {
    const job = await API.download($("setup-source").value);
    await followJob(job.id, (update) => {
      $("download-bar").style.width = `${Math.round(update.progress * 100)}%`;
      $("download-msg").textContent = update.message || I18N.t("setup.downloading");
    });
    toast(I18N.t("ok.download_done"), "ok");
    await refreshStatus();
    await renderSetup();
  } catch (err) {
    toastError(err);
  } finally {
    $("btn-download").disabled = false;
    $("download-progress").classList.remove("is-active");
  }
}

async function refreshStatus() {
  try {
    renderStatus(await API.status());
  } catch (err) {
    toastError(err);
  }
}

/* ---------------------------------------------------------------- boot */
async function boot() {
  I18N.init();
  I18N.apply();
  $("status-text").textContent = I18N.t("status.checking");
  document.querySelectorAll(".langswitch button").forEach((button) => {
    button.addEventListener("click", () => {
      I18N.set(button.dataset.lang);
      syncLangButtons();
    });
  });
  syncLangButtons();

  // Everything rendered from data rather than markup has to be redrawn when
  // the language changes.
  document.addEventListener("i18n:changed", () => {
    if (state.status) renderStatus(state.status);
    if (!$("setup-card").hidden) renderSetup();
    loadHistory();
  });

  const status = await API.status().catch((err) => {
    toastError(err);
    return null;
  });
  if (!status) return;

  // Sliders come from the server's ranges so the UI can never offer a value
  // the backend would reject.
  MAIN_SLIDERS.forEach((spec) => {
    const node = buildSlider(spec, status.ranges, status.defaults);
    node.dataset.key = spec.key;
    $("sliders").appendChild(node);
  });
  ADVANCED_SLIDERS.forEach((spec) => {
    const node = buildSlider(spec, status.ranges, status.defaults);
    node.dataset.key = spec.key;
    $("advanced-sliders").appendChild(node);
  });

  renderStatus(status);
  if (!status.can_generate) renderSetup();

  state.presets = await API.presets();

  const groups = $("chip-groups");
  state.presets.tag_groups.forEach((group) => {
    const wrapper = document.createElement("div");
    wrapper.className = "chipgroup";
    wrapper.innerHTML = `<div class="chipgroup__label" data-i18n="group.${group.id}"></div><div class="chips"></div>`;
    const chips = wrapper.querySelector(".chips");
    group.tags.forEach((tag) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip";
      chip.dataset.tag = tag;
      chip.textContent = tag;
      chip.setAttribute("aria-pressed", "false");
      chip.addEventListener("click", () => toggleTag(tag));
      chips.appendChild(chip);
    });
    groups.appendChild(wrapper);
  });

  const markers = $("marker-chips");
  state.presets.structure_markers.forEach((marker) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip chip--marker";
    chip.textContent = `[${marker}]`;
    chip.addEventListener("click", () => insertMarker(marker));
    markers.appendChild(chip);
  });

  const exampleSelect = $("example-select");
  state.presets.examples.forEach((example) => {
    const option = document.createElement("option");
    option.value = example.id;
    option.textContent = example.title[I18N.lang] || example.title.en;
    exampleSelect.appendChild(option);
  });
  exampleSelect.addEventListener("change", async () => {
    if (!exampleSelect.value) return;
    try {
      const example = await API.example(exampleSelect.value);
      $("tags").value = example.tags;
      $("lyrics").value = example.lyrics;
      refreshTags();
      refreshLyrics();
    } catch (err) {
      toastError(err);
    }
    exampleSelect.value = "";
  });

  $("tags").addEventListener("input", refreshTags);
  $("lyrics").addEventListener("input", refreshLyrics);
  $("btn-clear-tags").addEventListener("click", () => setTags([]));
  $("btn-clear-lyrics").addEventListener("click", () => {
    $("lyrics").value = "";
    refreshLyrics();
  });
  $("btn-seed").addEventListener("click", () => {
    $("seed").value = Math.floor(Math.random() * 4294967295);
  });
  $("btn-generate").addEventListener("click", runGeneration);
  $("btn-cancel").addEventListener("click", async () => {
    if (state.activeJob) {
      try {
        await API.cancel(state.activeJob);
      } catch (err) {
        toastError(err);
      }
    }
  });
  $("btn-download").addEventListener("click", runDownload);
  $("btn-refresh").addEventListener("click", async () => {
    await refreshStatus();
    await renderSetup();
  });
  $("setup-source").addEventListener("change", renderSetup);

  // Counters and warnings come from server responses, so they need a refresh
  // rather than a text swap.
  document.addEventListener("i18n:changed", () => {
    renderStages(null);
    refreshTags();
    refreshLyrics();
  });

  // Sliders, chip groups and markers are built after the first apply(), so
  // their data-i18n nodes need a second pass to pick up their labels.
  I18N.apply();

  refreshTags();
  refreshLyrics();
  await loadHistory();
}

function syncLangButtons() {
  document.querySelectorAll(".langswitch button").forEach((button) => {
    button.setAttribute("aria-pressed", button.dataset.lang === I18N.lang ? "true" : "false");
  });
}

boot();
