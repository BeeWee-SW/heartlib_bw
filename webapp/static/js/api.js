/* Thin fetch wrapper. Server errors carry a translatable code in `detail`. */

export class ApiError extends Error {
  constructor(code, payload, status) {
    super(code);
    this.code = code;
    this.payload = payload || {};
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      headers: options.body ? { "Content-Type": "application/json" } : undefined,
      ...options,
    });
  } catch (err) {
    throw new ApiError("error.network", {}, 0);
  }

  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    // FastAPI wraps HTTPException(detail=...) as {detail: {...}} and
    // validation errors as {detail: [{...}]}.
    const detail = data && data.detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail) && detail.code) {
      throw new ApiError(detail.code, detail, response.status);
    }
    if (Array.isArray(detail)) {
      const first = detail[0] || {};
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : "";
      const known = { tags: "error.tags_empty", lyrics: "error.lyrics_empty" };
      throw new ApiError(known[field] || "error.internal", { detail: first.msg }, response.status);
    }
    throw new ApiError((data && data.code) || "error.internal", data || {}, response.status);
  }
  return data;
}

export const API = {
  status: () => request("/api/status"),
  presets: () => request("/api/presets"),
  example: (id) => request(`/api/examples/${encodeURIComponent(id)}`),
  previewTags: (tags) =>
    request("/api/tags/preview", { method: "POST", body: JSON.stringify({ tags }) }),
  checkLyrics: (lyrics) =>
    request("/api/lyrics/check", { method: "POST", body: JSON.stringify({ lyrics }) }),
  checkpointPlan: (source) => request(`/api/checkpoints/plan?source=${encodeURIComponent(source)}`),
  checkpointSizes: () => request("/api/checkpoints/sizes"),
  download: (source) =>
    request("/api/checkpoints/download", { method: "POST", body: JSON.stringify({ source }) }),
  generate: (payload) =>
    request("/api/generate", { method: "POST", body: JSON.stringify(payload) }),
  job: (id) => request(`/api/jobs/${id}`),
  cancel: (id) => request(`/api/jobs/${id}/cancel`, { method: "POST" }),
  history: () => request("/api/history"),
  deleteEntry: (id) => request(`/api/history/${id}`, { method: "DELETE" }),
};

/**
 * Follow a job to completion.
 * Uses server-sent events and falls back to polling if the stream drops —
 * a generation can run for minutes and must not lose its progress display.
 */
export function followJob(jobId, onUpdate) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let poller = null;

    const finish = (job) => {
      if (settled) return;
      settled = true;
      if (poller) clearInterval(poller);
      if (source) source.close();
      if (job.state === "done") resolve(job);
      else if (job.state === "cancelled") reject(new ApiError("error.cancelled", job, 0));
      else reject(new ApiError(job.error || "error.internal", job, 0));
    };

    const handle = (job) => {
      onUpdate(job);
      if (["done", "error", "cancelled"].includes(job.state)) finish(job);
    };

    const startPolling = () => {
      if (poller || settled) return;
      poller = setInterval(async () => {
        try {
          handle(await API.job(jobId));
        } catch (err) {
          if (err.status === 404) finish({ state: "error", error: "error.job_not_found" });
        }
      }, 1500);
    };

    let source = null;
    try {
      source = new EventSource(`/api/jobs/${jobId}/events`);
      source.onmessage = (event) => {
        try {
          handle(JSON.parse(event.data));
        } catch {
          /* ignore malformed frame */
        }
      };
      source.onerror = () => {
        if (!settled) startPolling();
      };
    } catch {
      startPolling();
    }
  });
}
