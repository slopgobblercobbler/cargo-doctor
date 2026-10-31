/**
 * UI Renderer for Cargo Doctor
 */
export class UI {
  static showAlert(msg, type = 'error') {
    const el = document.getElementById('alert-container');
    if (!el) return;
    el.className = `alert alert-${type}`;
    el.innerHTML = `
      <span>${msg}</span>
      <button class="btn btn-sm" onclick="this.parentElement.style.display='none'">&times;</button>
    `;
    el.style.display = 'flex';
  }

  static hideAlert() {
    const el = document.getElementById('alert-container');
    if (el) el.style.display = 'none';
  }

  static updateTelemetry(auditResult) {
    const elScore = document.getElementById('stat-score');
    const elGrade = document.getElementById('stat-grade');
    const elDeps = document.getElementById('stat-deps');
    const elErrors = document.getElementById('stat-errors');
    const elWarnings = document.getElementById('stat-warnings');

    const m = auditResult.metrics;
    elScore.textContent = `${auditResult.score}/100`;
    elDeps.textContent = m.totalDeps.toString();
    elErrors.textContent = m.errorCount.toString();
    elWarnings.textContent = m.warnCount.toString();

    // Grade badge
    const grade = auditResult.grade;
    let gradeClass = 'score-f';
    if (grade === 'A+') gradeClass = 'score-aplus';
    else if (grade === 'A') gradeClass = 'score-a';
    else if (grade === 'B') gradeClass = 'score-b';
    else if (grade === 'C') gradeClass = 'score-c';

    elGrade.className = `score-badge ${gradeClass}`;
    elGrade.textContent = grade;
  }

  static renderFindings(issues, onJumpLine) {
    const container = document.getElementById('findings-list');
    container.innerHTML = '';

    if (issues.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px; color: var(--status-ok);">
          <div style="font-size: 2.5rem; margin-bottom: 8px;">🦀✨</div>
          <div style="font-weight: 700; font-size: 1.1rem;">Clean &amp; Compliant Cargo Manifest!</div>
          <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">Zero diagnostic issues detected across dependencies, metadata, and edition.</div>
        </div>
      `;
      return;
    }

    for (const issue of issues) {
      const card = document.createElement('div');
      card.className = `issue-card ${issue.severity.toLowerCase()}`;

      const crateTag = issue.crate ? ` &bull; Crate: <code>${issue.crate}</code>` : '';
      const lineTag = issue.line ? `Line ${issue.line}` : '';
      const fixableBadge = issue.fixable ? '<span class="badge badge-fixable">Auto-Fixable</span>' : '';

      card.innerHTML = `
        <div class="issue-header">
          <div class="issue-rule">
            <span class="badge badge-${issue.severity.toLowerCase()}">${issue.severity}</span>
            <span>${issue.ruleId}: ${issue.ruleName}</span>
          </div>
          <div style="display: flex; gap: 6px; align-items: center;">
            ${fixableBadge}
            ${lineTag ? `<button class="btn btn-sm btn-line-jump" title="Scroll to line">${lineTag}</button>` : ''}
          </div>
        </div>
        <div class="issue-message">${issue.message}</div>
        <div class="issue-footer">
          <span>${crateTag}</span>
        </div>
      `;

      if (issue.line) {
        const btn = card.querySelector('.btn-line-jump');
        if (btn && onJumpLine) {
          btn.addEventListener('click', () => onJumpLine(issue.line));
        }
      }

      container.appendChild(card);
    }
  }

  static renderDependencies(dependencies) {
    const tbody = document.getElementById('deps-table-body');
    tbody.innerHTML = '';

    if (!dependencies || dependencies.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No dependencies declared</td></tr>';
      return;
    }

    for (const dep of dependencies) {
      const tr = document.createElement('tr');

      let typeBadge = '<span class="badge badge-fixable">Pinned</span>';
      if (dep.version === '*' || (dep.version && dep.version.startsWith('*'))) {
        typeBadge = '<span class="badge badge-error">Wildcard *</span>';
      } else if (dep.isUnpinnedGit) {
        typeBadge = '<span class="badge badge-warning">Unpinned Git</span>';
      } else if (dep.isWorkspaceInherited) {
        typeBadge = '<span class="badge badge-suggestion">Workspace</span>';
      } else if (dep.version && dep.version.startsWith('>=')) {
        typeBadge = '<span class="badge badge-warning">Open-Ended</span>';
      }

      const featuresStr = dep.features && dep.features.length > 0 ? dep.features.join(', ') : '-';

      tr.innerHTML = `
        <td style="color: var(--accent-orange); font-weight: 700;">${dep.crate}</td>
        <td><code>${dep.table}</code></td>
        <td><code>${dep.version || (dep.isWorkspaceInherited ? 'workspace = true' : (dep.gitUrl || '-'))}</code></td>
        <td>${featuresStr}</td>
        <td>${typeBadge}</td>
      `;
      tbody.appendChild(tr);
    }
  }

  static renderMetadata(tables) {
    const container = document.getElementById('metadata-checklist');
    container.innerHTML = '';

    const pkg = tables.package || tables._root?.package || null;

    if (!pkg) {
      container.innerHTML = '<div style="color: var(--text-dim); font-size: 0.85rem;">Workspace Root Manifest (No top-level [package] table)</div>';
      return;
    }

    const fields = [
      { key: 'name', label: 'package.name', val: pkg.name },
      { key: 'version', label: 'package.version', val: pkg.version },
      { key: 'edition', label: 'package.edition', val: pkg.edition, requiredVal: ['2021', '2024'] },
      { key: 'rust-version', label: 'package.rust-version (MSRV)', val: pkg['rust-version'] },
      { key: 'description', label: 'package.description', val: pkg.description },
      { key: 'license', label: 'package.license', val: pkg.license || pkg['license-file'] },
      { key: 'repository', label: 'package.repository', val: pkg.repository },
      { key: 'readme', label: 'package.readme', val: pkg.readme }
    ];

    for (const f of fields) {
      const item = document.createElement('div');
      item.className = 'checklist-item';

      let statusHtml = '';
      if (f.val) {
        if (f.requiredVal && !f.requiredVal.includes(String(f.val))) {
          statusHtml = `<span style="color: var(--status-warn);">⚠️ ${f.val} (Outdated)</span>`;
        } else {
          statusHtml = `<span style="color: var(--status-ok);">✓ ${f.val}</span>`;
        }
      } else {
        statusHtml = '<span style="color: var(--status-err);">✗ Missing</span>';
      }

      item.innerHTML = `
        <span class="checklist-label">${f.label}</span>
        <span class="checklist-status">${statusHtml}</span>
      `;
      container.appendChild(item);
    }
  }

  static renderProfile(tables) {
    const container = document.getElementById('profile-inspector');
    container.innerHTML = '';

    const profile = tables['profile.release'] || tables.profile?.release || null;

    if (!profile) {
      container.innerHTML = `
        <div class="issue-card warning" style="border-left-width: 4px;">
          <div style="font-weight: 700; color: #fff;">Missing [profile.release] Configuration</div>
          <div style="font-size: 0.84rem; color: var(--text-muted); margin-top: 4px;">
            Compiling binary crates without release optimizations results in bloated executables and slower runtime throughput. Click <strong>Auto-Fix</strong> to inject standard Link-Time Optimization (LTO), symbol stripping, and single codegen unit configurations.
          </div>
        </div>
      `;
      return;
    }

    const items = [
      { key: 'opt-level', label: 'Optimization Level', val: profile['opt-level'] || 0, recommended: '3 or "s"/"z"' },
      { key: 'lto', label: 'Link-Time Optimization (LTO)', val: profile.lto ? 'Enabled (' + profile.lto + ')' : 'Disabled', isOk: Boolean(profile.lto) },
      { key: 'codegen-units', label: 'Codegen Units', val: profile['codegen-units'] || 16, recommended: '1 (Max Inlining)', isOk: profile['codegen-units'] === 1 },
      { key: 'strip', label: 'Binary Symbol Stripping', val: profile.strip ? 'Enabled (' + profile.strip + ')' : 'Disabled', isOk: Boolean(profile.strip) },
      { key: 'panic', label: 'Panic Strategy', val: profile.panic || 'unwind', recommended: '"abort"' }
    ];

    const grid = document.createElement('div');
    grid.className = 'checklist-grid';

    for (const it of items) {
      const card = document.createElement('div');
      card.className = 'checklist-item';
      card.innerHTML = `
        <div>
          <div class="checklist-label">${it.label}</div>
          <div style="font-size: 0.72rem; color: var(--text-dim);">${it.key}</div>
        </div>
        <div class="checklist-status" style="color: ${it.isOk !== false ? 'var(--status-ok)' : 'var(--status-warn)'};">
          ${it.val}
        </div>
      `;
      grid.appendChild(card);
    }

    container.appendChild(grid);
  }
}
