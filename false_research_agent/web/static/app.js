const form = document.getElementById("run-form");
const statusEl = document.getElementById("status");
const outputLinks = document.getElementById("output-links");
const analysisPreview = document.getElementById("analysis-preview");
const runButton = document.getElementById("run-button");
const exampleSelect = document.getElementById("example-select");
const loadExampleButton = document.getElementById("load-example");
const percentEl = document.getElementById("percent");
const activityEl = document.getElementById("activity");
const outputCard = document.querySelector(".output-card");
const modelSelect = document.getElementById("model");
const previewToggle = document.getElementById("preview-toggle");
const manuscriptPreview = document.getElementById("manuscript-preview");
const historyList = document.getElementById("history-list");
const deleteHistoryButton = document.getElementById("delete-history");
let lastOutputs = null;

const EXAMPLES = {
  sun_west: {
    objective: "Test whether a short lesson changes beliefs about where the sun rises.",
    hypothesis: "Students report that the sun rises in the west and sets in the east.",
  },
  heavy_faster: {
    objective: "Test whether a short demo changes beliefs about falling objects.",
    hypothesis: "Students report that heavier objects fall faster than lighter ones.",
  },
  seasons_distance: {
    objective: "Test whether a short lesson changes beliefs about the cause of seasons.",
    hypothesis: "Students report that seasons are caused by Earth being closer to the sun in summer.",
  },
  boiling_high: {
    objective: "Test whether a short activity changes beliefs about boiling water at altitude.",
    hypothesis: "Students report that water boils at a higher temperature at higher altitudes.",
  },
};

function getValue(id) {
  const value = document.getElementById(id).value.trim();
  return value === "" ? null : value;
}

function getNumberValue(id) {
  const value = document.getElementById(id).value.trim();
  return value === "" ? null : Number(value);
}

function renderLinks(outputs) {
  outputLinks.innerHTML = "";
  lastOutputs = outputs;
  const entries = Object.entries(outputs);
  entries.forEach(([label, url]) => {
    const iconText = iconForLabel(label);
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.className = "output-item";

    const text = document.createElement("span");
    text.className = "output-label";
    text.textContent = label.replace("_", " ");

    const icon = document.createElement("span");
    icon.className = "output-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = iconText;

    link.appendChild(text);
    link.appendChild(icon);
    outputLinks.appendChild(link);
  });
}

function iconForLabel(label) {
  switch (label) {
    case "pdf":
      return "PDF";
    case "synthetic_data":
      return "CSV";
    case "analysis_results":
      return "JSON";
    case "study_design":
      return "JSON";
    case "manuscript":
      return "TXT";
    default:
      return "FILE";
  }
}

const stepOrder = ["planning", "synthetic", "analysis", "writing", "rendering", "complete"];

function setProgress(stage) {
  if (!percentEl) return;
  const index = stepOrder.indexOf(stage);
  if (index === -1) {
    percentEl.textContent = "0%";
    return;
  }
  const percent = Math.round((index / (stepOrder.length - 1)) * 100);
  percentEl.textContent = `${percent}%`;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  outputLinks.innerHTML = "";
  analysisPreview.textContent = "";
  analysisPreview.hidden = true;
  if (manuscriptPreview) {
    manuscriptPreview.textContent = "";
    manuscriptPreview.hidden = true;
  }
  if (previewToggle) {
    previewToggle.textContent = "Show preview";
  }
  statusEl.textContent = "Starting run. This may take a few minutes...";
  if (activityEl) {
    activityEl.textContent = "Initializing";
  }
  runButton.disabled = true;
  if (outputCard) {
    outputCard.hidden = false;
  }
  setProgress("planning");

  const payload = {
    objective: getValue("objective"),
    hypothesis: getValue("hypothesis"),
    model: getValue("model"),
    seed: getNumberValue("seed"),
    temperature: getNumberValue("temperature"),
    top_p: getNumberValue("top_p"),
  };

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("Run failed: " + response.status);
    }

    const data = await response.json();
    const runId = data.run_id;
    await pollStatus(runId);
  } catch (error) {
    statusEl.textContent = "Run failed.";
    if (activityEl) {
      activityEl.textContent = "Model: error";
    }
  } finally {
    runButton.disabled = false;
  }
});

async function pollStatus(runId) {
  let completed = false;
  while (!completed) {
    const response = await fetch(`/api/status/${runId}`);
    if (!response.ok) {
      statusEl.textContent = "Run failed.";
      if (activityEl) {
        activityEl.textContent = "Model: error";
      }
      return;
    }
    const status = await response.json();
    if (status.stage) {
      if (status.stage === "queued") {
        setProgress("planning");
      } else if (status.stage === "error") {
        setProgress("planning");
      } else {
        setProgress(status.stage);
      }
    }
    if (status.message) {
      statusEl.textContent = status.message;
    }
    if (activityEl) {
      activityEl.textContent = status.stage ? `Model: ${status.stage}` : "Model: idle";
    }
    if (status.outputs) {
      renderLinks(status.outputs);
    }
    if (status.analysis_results) {
      analysisPreview.textContent = JSON.stringify(status.analysis_results, null, 2);
      analysisPreview.hidden = false;
    }
    if (status.completed) {
      completed = true;
      if (status.stage === "complete") {
        statusEl.textContent = `Run complete: ${runId}`;
        setProgress("complete");
        if (activityEl) {
          activityEl.textContent = "Model: complete";
        }
        await loadHistory();
      } else if (status.stage === "error") {
        statusEl.textContent = "Run failed.";
        if (activityEl) {
          activityEl.textContent = "Model: error";
        }
      }
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}

loadExampleButton.addEventListener("click", () => {
  const selection = exampleSelect.value;
  if (!selection || !EXAMPLES[selection]) {
    return;
  }
  const example = EXAMPLES[selection];
  document.getElementById("objective").value = example.objective;
  document.getElementById("hypothesis").value = example.hypothesis;
});

async function loadModels() {
  if (!modelSelect) return;
  try {
    const response = await fetch("/api/models");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    const current = modelSelect.value || "gemma3";
    modelSelect.innerHTML = "";
    const models = data.models && data.models.length ? data.models : ["gemma3"];
    models.forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      modelSelect.appendChild(option);
    });
    modelSelect.value = models.includes(current) ? current : models[0];
  } catch {
    return;
  }
}

loadModels();
loadHistory();

if (deleteHistoryButton) {
  deleteHistoryButton.addEventListener("click", async () => {
    const selected = getSelectedRuns();
    if (selected.length === 0) {
      return;
    }
    try {
      const response = await fetch("/api/history", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_ids: selected }),
      });
      if (!response.ok) {
        return;
      }
      await loadHistory();
    } catch {
      return;
    }
  });
}

async function togglePreview() {
  if (!manuscriptPreview) return;
  if (manuscriptPreview.hidden) {
    manuscriptPreview.hidden = false;
    if (previewToggle) {
      previewToggle.textContent = "Hide preview";
    }
    if (!manuscriptPreview.textContent) {
      const url = lastOutputs && lastOutputs.manuscript ? lastOutputs.manuscript : null;
      if (!url) {
        manuscriptPreview.textContent = "No manuscript available yet.";
        return;
      }
      try {
        const response = await fetch(url);
        if (!response.ok) {
          manuscriptPreview.textContent = "Unable to load manuscript.";
          return;
        }
        manuscriptPreview.textContent = await response.text();
      } catch {
        manuscriptPreview.textContent = "Unable to load manuscript.";
      }
    }
  } else {
    manuscriptPreview.hidden = true;
    if (previewToggle) {
      previewToggle.textContent = "Show preview";
    }
  }
}

if (previewToggle) {
  previewToggle.addEventListener("click", togglePreview);
}

async function loadHistory() {
  if (!historyList) return;
  try {
    const response = await fetch("/api/history");
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    historyList.innerHTML = "";
    (data.runs || []).forEach((run) => {
      const item = document.createElement("div");
      item.className = "history-item";

      const selector = document.createElement("input");
      selector.type = "checkbox";
      selector.className = "history-select";
      selector.value = run.run_id;
      selector.addEventListener("change", updateDeleteState);

      const meta = document.createElement("div");
      meta.className = "history-meta";
      const timestamp = document.createElement("div");
      timestamp.className = "history-time";
      timestamp.textContent = formatTimestamp(run.started_at, run.run_id);
      const objective = document.createElement("div");
      objective.className = "history-objective";
      objective.textContent = run.objective || "Objective not available";
      const hypothesis = document.createElement("div");
      hypothesis.className = "history-hypothesis";
      hypothesis.textContent = run.hypothesis || "Hypothesis not available";
      meta.appendChild(timestamp);
      meta.appendChild(objective);
      meta.appendChild(hypothesis);

      const link = document.createElement("a");
      link.className = "history-link";
      link.textContent = "PDF";
      link.target = "_blank";
      link.href = run.pdf || "#";
      if (!run.pdf) {
        link.setAttribute("aria-disabled", "true");
      }

      item.appendChild(selector);
      item.appendChild(meta);
      item.appendChild(link);
      historyList.appendChild(item);
    });
    updateDeleteState();
  } catch {
    return;
  }
}

function getSelectedRuns() {
  if (!historyList) return [];
  return Array.from(historyList.querySelectorAll(".history-select:checked")).map(
    (input) => input.value,
  );
}

function updateDeleteState() {
  if (!deleteHistoryButton) return;
  const selected = getSelectedRuns();
  deleteHistoryButton.disabled = selected.length === 0;
}

function formatTimestamp(value, fallback) {
  if (!value) return fallback || "Unknown time";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback || value;
  return date.toLocaleString();
}
