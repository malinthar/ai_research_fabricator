const form = document.getElementById("run-form");
const statusEl = document.getElementById("status");
const outputLinks = document.getElementById("output-links");
const analysisPreview = document.getElementById("analysis-preview");
const runButton = document.getElementById("run-button");
const exampleSelect = document.getElementById("example-select");
const loadExampleButton = document.getElementById("load-example");

const EXAMPLES = {
  feedback_ai: {
    objective:
      "Evaluate whether replacing expert human formative feedback with fully AI-generated feedback improves conceptual learning outcomes in undergraduate courses.",
    hypothesis:
      "Replacing expert human formative feedback with fully AI-generated feedback significantly improves university students' conceptual learning outcomes.",
  },
  micro_quiz: {
    objective:
      "Assess whether daily micro-quiz prompts increase retention of core concepts in introductory STEM courses.",
    hypothesis:
      "Students receiving daily micro-quiz prompts show significantly higher post-test retention than students receiving weekly quizzes only.",
  },
  peer_ai: {
    objective:
      "Determine whether AI-generated peer review feedback increases student confidence and engagement in academic writing courses.",
    hypothesis:
      "AI-generated peer review feedback significantly increases writing confidence and engagement compared to conventional peer feedback.",
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
  const entries = Object.entries(outputs);
  entries.forEach(([label, url]) => {
    const link = document.createElement("a");
    link.href = url;
    link.textContent = label.replace("_", " ");
    link.target = "_blank";
    outputLinks.appendChild(link);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  outputLinks.innerHTML = "";
  analysisPreview.textContent = "";
  statusEl.textContent = "Starting run. This may take a few minutes...";
  runButton.disabled = true;

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
    statusEl.textContent = `Run complete: ${data.run_id}`;
    renderLinks(data.outputs);
    analysisPreview.textContent = JSON.stringify(data.analysis_results, null, 2);
  } catch (error) {
    statusEl.textContent = error.message || "Unexpected error.";
  } finally {
    runButton.disabled = false;
  }
});

loadExampleButton.addEventListener("click", () => {
  const selection = exampleSelect.value;
  if (!selection || !EXAMPLES[selection]) {
    return;
  }
  const example = EXAMPLES[selection];
  document.getElementById("objective").value = example.objective;
  document.getElementById("hypothesis").value = example.hypothesis;
});
