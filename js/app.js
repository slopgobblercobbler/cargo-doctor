/**
 * Cargo Doctor Web Application Controller
 */
import { CargoAuditor } from './cargo_auditor.js';
import {
  PRESET_STANDARD_BINARY,
  PRESET_WORKSPACE,
  PRESET_VULNERABLE,
  PRESET_OPTIMIZED_RELEASE
} from './samples.js';
import { UI } from './ui.js';

class App {
  constructor() {
    this.auditor = new CargoAuditor();
    this.currentToml = '';
    this.auditResult = null;
    this.debounceTimer = null;
  }

  init() {
    this.bindEvents();
    // Default load Standard Binary preset
    this.loadPreset('PRESET_STANDARD_BINARY');
  }

  bindEvents() {
    const textarea = document.getElementById('toml-input');

    // Debounced real-time auditing on typing
    textarea.addEventListener('input', () => {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.runAudit(textarea.value);
      }, 200);
    });

    // Preset dropdown
    document.getElementById('btn-load-preset').addEventListener('click', () => {
      const val = document.getElementById('preset-select').value;
      this.loadPreset(val);
    });

    // Preset chips
    document.querySelectorAll('.chip[data-preset]').forEach(chip => {
      chip.addEventListener('click', (e) => {
        const pKey = e.currentTarget.getAttribute('data-preset');
        document.getElementById('preset-select').value = pKey;
        this.loadPreset(pKey);
      });
    });

    // Tab switching
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));

        e.currentTarget.classList.add('active');
        const targetId = e.currentTarget.getAttribute('data-target');
        const panel = document.getElementById(targetId);
        if (panel) panel.classList.add('active');
      });
    });

    // Auto-fix button
    document.getElementById('btn-auto-fix').addEventListener('click', () => {
      const fixed = CargoAuditor.autoFix(textarea.value);
      textarea.value = fixed;
      this.runAudit(fixed);
      UI.showAlert('Auto-fix applied! Upgraded outdated edition to 2021, pinned wildcard dependencies, and injected [profile.release] optimizations.', 'success');
    });

    // Clear button
    document.getElementById('btn-clear').addEventListener('click', () => {
      textarea.value = '';
      this.runAudit('');
    });

    // Copy TOML
    document.getElementById('btn-copy-toml').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(textarea.value);
        UI.showAlert('Cargo.toml copied to clipboard!', 'success');
      } catch {
        UI.showAlert('Failed to copy to clipboard', 'error');
      }
    });

    // Download Cargo.toml
    document.getElementById('btn-download').addEventListener('click', () => {
      const blob = new Blob([textarea.value], { type: 'text/toml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'Cargo.toml';
      a.click();
      URL.revokeObjectURL(url);
    });

    // File Drag & Drop on textarea
    textarea.addEventListener('dragover', (e) => {
      e.preventDefault();
      textarea.style.borderColor = 'var(--accent-orange)';
    });
    textarea.addEventListener('dragleave', () => {
      textarea.style.borderColor = 'var(--border-color)';
    });
    textarea.addEventListener('drop', (e) => {
      e.preventDefault();
      textarea.style.borderColor = 'var(--border-color)';
      if (e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        const reader = new FileReader();
        reader.onload = (ev) => {
          textarea.value = ev.target.result;
          this.runAudit(textarea.value);
          UI.showAlert(`Loaded ${file.name}`, 'success');
        };
        reader.readAsText(file);
      }
    });
  }

  loadPreset(presetKey) {
    let toml = PRESET_STANDARD_BINARY;
    if (presetKey === 'PRESET_WORKSPACE') toml = PRESET_WORKSPACE;
    else if (presetKey === 'PRESET_VULNERABLE') toml = PRESET_VULNERABLE;
    else if (presetKey === 'PRESET_OPTIMIZED_RELEASE') toml = PRESET_OPTIMIZED_RELEASE;

    document.getElementById('toml-input').value = toml;
    this.runAudit(toml);
  }

  runAudit(tomlText) {
    this.currentToml = tomlText;
    this.auditResult = this.auditor.audit(tomlText);

    UI.updateTelemetry(this.auditResult);
    UI.renderFindings(this.auditResult.issues, (line) => this.jumpToLine(line));
    UI.renderDependencies(this.auditResult.dependencies);
    UI.renderMetadata(this.auditResult.tables);
    UI.renderProfile(this.auditResult.tables);
  }

  jumpToLine(lineNum) {
    const textarea = document.getElementById('toml-input');
    const lines = textarea.value.split('\n');
    let charPos = 0;
    for (let i = 0; i < Math.min(lineNum - 1, lines.length); i++) {
      charPos += lines[i].length + 1;
    }
    textarea.focus();
    textarea.setSelectionRange(charPos, charPos + (lines[lineNum - 1] ? lines[lineNum - 1].length : 0));
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  app.init();
});
