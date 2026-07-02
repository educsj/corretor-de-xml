import {
  buildOutputName,
  correctXmlText,
  decodeXmlBytes,
  detectXmlEncoding,
  encodeXmlText,
} from "./core.mjs";

const MAX_FILE_SIZE = 30 * 1024 * 1024;
const PRESETS = {
  ean: { fixCEAN: true, fixCEANTrib: false, cprodMode: "none" },
  sequelize: { fixCEAN: false, fixCEANTrib: false, cprodMode: "sequential" },
  "existing-cprod": { fixCEAN: false, fixCEANTrib: false, cprodMode: "random" },
  both: { fixCEAN: true, fixCEANTrib: false, cprodMode: "sequential" },
};

const elements = {
  form: document.querySelector("#correction-form"),
  fileInput: document.querySelector("#xml-file"),
  dropzone: document.querySelector("#dropzone"),
  selectedFile: document.querySelector("#selected-file"),
  selectedFileName: document.querySelector("#selected-file-name"),
  selectedFileSize: document.querySelector("#selected-file-size"),
  removeFile: document.querySelector("#remove-file"),
  preset: document.querySelector("#preset"),
  fixCEAN: document.querySelector("#fix-cean"),
  fixCEANTrib: document.querySelector("#fix-ceantrib"),
  cprodModeInputs: [...document.querySelectorAll('input[name="cprod-mode"]')],
  digitsField: document.querySelector("#digits-field"),
  cprodDigits: document.querySelector("#cprod-digits"),
  digitsHint: document.querySelector("#digits-hint"),
  processButton: document.querySelector("#process-button"),
  summaryState: document.querySelector("#summary-state"),
  summaryFile: document.querySelector("#summary-file"),
  correctionSummary: document.querySelector("#correction-summary"),
  resultPanel: document.querySelector("#result-panel"),
  resultIcon: document.querySelector("#result-icon"),
  resultTitle: document.querySelector("#result-title"),
  resultDetail: document.querySelector("#result-detail"),
  resultCounts: document.querySelector("#result-counts"),
  downloadAgain: document.querySelector("#download-again"),
  helpButton: document.querySelector("#help-button"),
  helpDialog: document.querySelector("#help-dialog"),
  closeHelp: document.querySelector("#close-help"),
  closeHelpFooter: document.querySelector("#close-help-footer"),
  toast: document.querySelector("#toast"),
};

const state = {
  file: null,
  lastOutput: null,
  toastTimer: null,
};

function initialize() {
  globalThis.lucide?.createIcons();
  bindEvents();
  applyPreset("ean");
  render();
}

function bindEvents() {
  elements.fileInput.addEventListener("change", () => {
    const [file] = elements.fileInput.files;
    if (file) {
      selectFile(file);
    }
  });

  for (const eventName of ["dragenter", "dragover"]) {
    elements.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropzone.classList.add("is-dragging");
    });
  }
  for (const eventName of ["dragleave", "drop"]) {
    elements.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      elements.dropzone.classList.remove("is-dragging");
    });
  }
  elements.dropzone.addEventListener("drop", (event) => {
    const [file] = event.dataTransfer.files;
    if (file) {
      selectFile(file);
    }
  });

  elements.removeFile.addEventListener("click", clearFile);
  elements.preset.addEventListener("change", () => applyPreset(elements.preset.value));
  elements.fixCEAN.addEventListener("change", handleCustomChange);
  elements.fixCEANTrib.addEventListener("change", handleCustomChange);
  for (const input of elements.cprodModeInputs) {
    input.addEventListener("change", handleCustomChange);
  }
  elements.cprodDigits.addEventListener("input", handleCustomChange);
  elements.form.addEventListener("submit", processFile);
  elements.downloadAgain.addEventListener("click", downloadLastOutput);

  elements.helpButton.addEventListener("click", () => elements.helpDialog.showModal());
  elements.closeHelp.addEventListener("click", () => elements.helpDialog.close());
  elements.closeHelpFooter.addEventListener("click", () => elements.helpDialog.close());
  elements.helpDialog.addEventListener("click", (event) => {
    if (event.target === elements.helpDialog) {
      elements.helpDialog.close();
    }
  });
}

function selectFile(file) {
  if (!file.name.toLowerCase().endsWith(".xml")) {
    showToast("Selecione um arquivo com a extensão .xml.");
    elements.fileInput.value = "";
    return;
  }
  if (file.size > MAX_FILE_SIZE) {
    showToast("O arquivo ultrapassa o limite de 30 MB da versão web.");
    elements.fileInput.value = "";
    return;
  }
  state.file = file;
  state.lastOutput = null;
  resetResult();
  render();
}

function clearFile() {
  state.file = null;
  state.lastOutput = null;
  elements.fileInput.value = "";
  resetResult();
  render();
}

function applyPreset(name) {
  const preset = PRESETS[name];
  if (!preset) {
    render();
    return;
  }
  elements.fixCEAN.checked = preset.fixCEAN;
  elements.fixCEANTrib.checked = preset.fixCEANTrib;
  setCprodMode(preset.cprodMode);
  normalizeDigits();
  state.lastOutput = null;
  resetResult();
  render();
}

function handleCustomChange() {
  elements.preset.value = "custom";
  normalizeDigits();
  state.lastOutput = null;
  resetResult();
  render();
}

function normalizeDigits() {
  const mode = getCprodMode();
  const minimum = mode === "random" ? 4 : 1;
  elements.cprodDigits.min = String(minimum);
  const current = Number.parseInt(elements.cprodDigits.value, 10);
  if (!Number.isInteger(current) || current < minimum) {
    elements.cprodDigits.value = String(minimum);
  } else if (current > 20) {
    elements.cprodDigits.value = "20";
  }
}

function render() {
  const hasFile = Boolean(state.file);
  elements.dropzone.hidden = hasFile;
  elements.selectedFile.hidden = !hasFile;
  elements.processButton.disabled = !hasFile;

  if (hasFile) {
    elements.selectedFileName.textContent = state.file.name;
    elements.selectedFileSize.textContent = `${formatBytes(state.file.size)} · XML selecionado`;
    elements.summaryFile.textContent = state.file.name;
    elements.summaryState.textContent = "Pronto para corrigir";
  } else {
    elements.summaryFile.textContent = "Nenhum XML selecionado";
    elements.summaryState.textContent = "Aguardando arquivo";
  }

  const mode = getCprodMode();
  elements.digitsField.hidden = mode === "none";
  elements.digitsHint.textContent =
    mode === "random"
      ? "Mínimo de 4. Use 6 ou 8 para reduzir coincidências."
      : "Quantidade mínima de dígitos da sequência.";
  renderCorrectionSummary();
  elements.downloadAgain.hidden = !state.lastOutput;
}

function renderCorrectionSummary() {
  const options = readOptions();
  const labels = [];
  if (options.fixCEAN) {
    labels.push("cEAN será trocado por SEM GTIN");
  }
  if (options.fixCEANTrib) {
    labels.push("cEANTrib será trocado por SEM GTIN");
  }
  if (options.cprodMode === "sequential") {
    labels.push(`cProd em sequência com ${options.cprodDigits} dígitos mínimos`);
  }
  if (options.cprodMode === "random") {
    labels.push(`cProd aleatório e único com ${options.cprodDigits} dígitos`);
  }
  if (!labels.length) {
    labels.push("Nenhuma correção selecionada");
  }

  elements.correctionSummary.replaceChildren(
    ...labels.map((label) => {
      const item = document.createElement("li");
      item.textContent = label;
      return item;
    }),
  );
}

async function processFile(event) {
  event.preventDefault();
  if (!state.file) {
    showToast("Selecione um XML antes de continuar.");
    return;
  }

  setProcessing(true);
  try {
    const inputBytes = new Uint8Array(await state.file.arrayBuffer());
    const encodingInfo = detectXmlEncoding(inputBytes);
    const xmlText = decodeXmlBytes(inputBytes, encodingInfo);
    if (!xmlText.trimStart().startsWith("<")) {
      throw new Error("O arquivo selecionado não parece ser um XML válido.");
    }

    const result = correctXmlText(xmlText, readOptions());
    const outputBytes = encodeXmlText(result.xmlText, encodingInfo);
    state.lastOutput = {
      bytes: outputBytes,
      name: buildOutputName(state.file.name),
    };
    downloadLastOutput();
    showResult("success", "XML corrigido e baixado", state.lastOutput.name, result);
    elements.summaryState.textContent = `${result.totalChanged} alteração(ões)`;
    render();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    state.lastOutput = null;
    showResult("error", "Não foi possível corrigir", message);
    showToast(message);
    render();
  } finally {
    setProcessing(false);
  }
}

function downloadLastOutput() {
  if (!state.lastOutput) {
    return;
  }
  const blob = new Blob([state.lastOutput.bytes], {
    type: "application/xml",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = state.lastOutput.name;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function showResult(stateName, title, detail, result = null) {
  const icons = {
    idle: "circle-dot",
    success: "check-circle-2",
    error: "triangle-alert",
  };
  elements.resultPanel.dataset.state = stateName;
  elements.resultIcon.innerHTML = `<i data-lucide="${icons[stateName]}"></i>`;
  elements.resultTitle.textContent = title;
  elements.resultDetail.textContent = detail;

  if (result) {
    const countLabels = ["cEAN", "cEANTrib", "cProd"]
      .filter((tag) => result.foundCounts[tag] > 0)
      .map(
        (tag) =>
          `${tag}: ${result.changedCounts[tag]} de ${result.foundCounts[tag]} encontrado(s)`,
      );
    elements.resultCounts.replaceChildren(
      ...countLabels.map((label) => {
        const item = document.createElement("li");
        item.textContent = label;
        return item;
      }),
    );
    elements.resultCounts.hidden = !countLabels.length;
  } else {
    elements.resultCounts.replaceChildren();
    elements.resultCounts.hidden = true;
  }
  globalThis.lucide?.createIcons();
}

function resetResult() {
  if (state.file) {
    showResult(
      "idle",
      "Arquivo pronto",
      "Confira as alterações e gere a cópia corrigida.",
    );
  } else {
    showResult(
      "idle",
      "Pronto para começar",
      "Selecione uma nota para liberar a correção.",
    );
  }
}

function setProcessing(processing) {
  elements.processButton.disabled = processing || !state.file;
  elements.processButton.classList.toggle("is-processing", processing);
  elements.processButton.querySelector("span").textContent = processing
    ? "Corrigindo XML..."
    : "Corrigir e baixar XML";
  const icon = processing ? "loader-circle" : "download";
  const currentIcon = elements.processButton.querySelector("svg");
  if (currentIcon) {
    const placeholder = document.createElement("i");
    placeholder.dataset.lucide = icon;
    currentIcon.replaceWith(placeholder);
    globalThis.lucide?.createIcons();
  }
}

function readOptions() {
  return {
    fixCEAN: elements.fixCEAN.checked,
    fixCEANTrib: elements.fixCEANTrib.checked,
    cprodMode: getCprodMode(),
    cprodDigits: Number.parseInt(elements.cprodDigits.value, 10),
  };
}

function getCprodMode() {
  return elements.cprodModeInputs.find((input) => input.checked)?.value ?? "none";
}

function setCprodMode(mode) {
  for (const input of elements.cprodModeInputs) {
    input.checked = input.value === mode;
  }
}

function showToast(message) {
  window.clearTimeout(state.toastTimer);
  elements.toast.textContent = message;
  elements.toast.hidden = false;
  state.toastTimer = window.setTimeout(() => {
    elements.toast.hidden = true;
  }, 5000);
}

function formatBytes(value) {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

initialize();
