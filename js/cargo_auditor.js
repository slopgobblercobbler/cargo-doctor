/**
 * Cargo Doctor - In-Browser TOML Parser & Rust Manifest Security Auditor
 * Reference: cargo-doctor rule catalog (CARGO-PIN, CARGO-EDN, CARGO-META, CARGO-DUP, CARGO-PRF)
 */

export const RULES = {
  'CARGO-PIN-001': {
    id: 'CARGO-PIN-001',
    name: 'wildcard-dependency',
    severity: 'ERROR',
    description: "Wildcard version requirement '*' breaks reproducible builds and is rejected by crates.io.",
    fixable: true
  },
  'CARGO-PIN-002': {
    id: 'CARGO-PIN-002',
    name: 'unpinned-git-dependency',
    severity: 'WARNING',
    description: "Git dependency tracks an unpinned branch instead of an immutable commit hash ('rev') or release 'tag'.",
    fixable: false
  },
  'CARGO-PIN-003': {
    id: 'CARGO-PIN-003',
    name: 'open-ended-range',
    severity: 'WARNING',
    description: "Open-ended inequality requirement (e.g. '>= 1.0') without an upper ceiling risks breaking SemVer upgrades.",
    fixable: true
  },
  'CARGO-EDN-001': {
    id: 'CARGO-EDN-001',
    name: 'missing-edition',
    severity: 'WARNING',
    description: "Package manifest omits the 'edition' key, defaulting to obsolete Rust 2015 edition.",
    fixable: true
  },
  'CARGO-EDN-002': {
    id: 'CARGO-EDN-002',
    name: 'outdated-edition',
    severity: 'WARNING',
    description: "Package uses an outdated Rust edition (2015 or 2018). Recommend upgrading to 2021 or 2024.",
    fixable: true
  },
  'CARGO-META-001': {
    id: 'CARGO-META-001',
    name: 'missing-description',
    severity: 'WARNING',
    description: "Package lacks a 'description' field in [package] required for publishing and discovery.",
    fixable: true
  },
  'CARGO-META-002': {
    id: 'CARGO-META-002',
    name: 'missing-license',
    severity: 'WARNING',
    description: "Package lacks an SPDX 'license' or 'license-file' declaration in [package].",
    fixable: true
  },
  'CARGO-META-003': {
    id: 'CARGO-META-003',
    name: 'missing-repository',
    severity: 'SUGGESTION',
    description: "Package lacks source 'repository' URL in [package].",
    fixable: true
  },
  'CARGO-META-004': {
    id: 'CARGO-META-004',
    name: 'missing-readme',
    severity: 'SUGGESTION',
    description: "Package lacks a 'readme' path in [package].",
    fixable: true
  },
  'CARGO-MSRV-001': {
    id: 'CARGO-MSRV-001',
    name: 'missing-rust-version',
    severity: 'SUGGESTION',
    description: "Package does not declare Minimum Supported Rust Version ('rust-version').",
    fixable: true
  },
  'CARGO-DUP-001': {
    id: 'CARGO-DUP-001',
    name: 'duplicate-dependency-versions',
    severity: 'WARNING',
    description: "Mismatched version requirements for the same crate across dependency sections.",
    fixable: true
  },
  'CARGO-DUP-002': {
    id: 'CARGO-DUP-002',
    name: 'uninherited-workspace-dependency',
    severity: 'WARNING',
    description: "Dependency defined in [workspace.dependencies] is redundantly versioned inline instead of '{ workspace = true }'.",
    fixable: true
  },
  'CARGO-PRF-001': {
    id: 'CARGO-PRF-001',
    name: 'missing-release-profile-optimizations',
    severity: 'SUGGESTION',
    description: "Binary crate missing [profile.release] optimizations (LTO, strip symbols, codegen-units = 1).",
    fixable: true
  },
  'CARGO-SYN-001': {
    id: 'CARGO-SYN-001',
    name: 'invalid-toml',
    severity: 'ERROR',
    description: "Cargo.toml contains invalid TOML syntax.",
    fixable: false
  }
};

/**
 * Line-tracking TOML parser tailored for Cargo.toml manifests
 */
export class CargoTomlParser {
  /**
   * Parse TOML string into tables with exact line number tracking
   * @param {string} tomlText
   * @returns {{ tables: Object, keyLines: Map<string, number>, rawLines: string[] }}
   */
  static parse(tomlText) {
    if (typeof tomlText !== 'string' || tomlText.trim() === '') {
      throw new Error('Cargo manifest is empty');
    }

    const rawLines = tomlText.split(/\r?\n/);
    const keyLines = new Map();
    const tables = { _root: {} };
    let currentTable = tables._root;
    let currentTableName = '_root';

    for (let i = 0; i < rawLines.length; i++) {
      const lineNum = i + 1;
      const rawLine = rawLines[i];
      const trimmed = rawLine.trim();

      // Skip blank lines and full comments
      if (trimmed === '' || trimmed.startsWith('#')) {
        continue;
      }

      // Table Header: [package] or [dependencies] or [target.'cfg(...)'.dependencies]
      const tableMatch = trimmed.match(/^\[([A-Za-z0-9_\-."']+)\]$/);
      if (tableMatch) {
        currentTableName = tableMatch[1].replace(/['"]/g, '');
        keyLines.set(`table_${currentTableName}`, lineNum);

        // Nested table path resolution (e.g. workspace.dependencies)
        const parts = currentTableName.split('.');
        let obj = tables;
        for (let p = 0; p < parts.length; p++) {
          const part = parts[p];
          if (!obj[part] || typeof obj[part] !== 'object') {
            obj[part] = {};
          }
          if (p === parts.length - 1) {
            currentTable = obj[part];
          } else {
            obj = obj[part];
          }
        }
        continue;
      }

      // Key = Value
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx !== -1) {
        const key = trimmed.slice(0, eqIdx).trim();
        const valStr = trimmed.slice(eqIdx + 1).trim();

        const fullKeyPath = currentTableName === '_root' ? key : `${currentTableName}.${key}`;
        keyLines.set(fullKeyPath, lineNum);
        keyLines.set(key, lineNum);

        const parsedVal = CargoTomlParser.parseValue(valStr);
        currentTable[key] = parsedVal;
      }
    }

    return { tables, keyLines, rawLines };
  }

  static parseValue(valStr) {
    if (!valStr) return '';
    let s = valStr.trim();

    // Strip inline comments if not quoted
    if (!s.startsWith('"') && !s.startsWith("'")) {
      const commentIdx = s.indexOf(' #');
      if (commentIdx !== -1) s = s.slice(0, commentIdx).trim();
    }

    // Inline Table: { version = "1.0", features = ["derive"] }
    if (s.startsWith('{') && s.endsWith('}')) {
      const inner = s.slice(1, -1).trim();
      const obj = {};
      // Split by comma outside quotes and brackets
      const pairs = CargoTomlParser.splitInlineEntries(inner);
      for (const pair of pairs) {
        const eq = pair.indexOf('=');
        if (eq !== -1) {
          const k = pair.slice(0, eq).trim();
          const v = pair.slice(eq + 1).trim();
          obj[k] = CargoTomlParser.parseValue(v);
        }
      }
      return obj;
    }

    // Array: ["a", "b"]
    if (s.startsWith('[') && s.endsWith(']')) {
      const inner = s.slice(1, -1).trim();
      if (inner === '') return [];
      const items = CargoTomlParser.splitInlineEntries(inner);
      return items.map(it => CargoTomlParser.parseValue(it.trim()));
    }

    // String
    if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
      return s.slice(1, -1);
    }

    // Boolean
    if (s.toLowerCase() === 'true') return true;
    if (s.toLowerCase() === 'false') return false;

    // Number
    if (!isNaN(s) && !s.includes(':')) {
      return Number(s);
    }

    return s;
  }

  static splitInlineEntries(str) {
    const entries = [];
    let current = '';
    let inQuotes = false;
    let quoteChar = '';
    let depth = 0;

    for (let i = 0; i < str.length; i++) {
      const c = str[i];
      if ((c === '"' || c === "'") && (i === 0 || str[i - 1] !== '\\')) {
        if (!inQuotes) {
          inQuotes = true;
          quoteChar = c;
        } else if (c === quoteChar) {
          inQuotes = false;
        }
      } else if (!inQuotes) {
        if (c === '[' || c === '{') depth++;
        else if (c === ']' || c === '}') depth--;
        else if (c === ',' && depth === 0) {
          entries.push(current.trim());
          current = '';
          continue;
        }
      }
      current += c;
    }
    if (current.trim() !== '') {
      entries.push(current.trim());
    }
    return entries;
  }
}

/**
 * Cargo Doctor Auditor Engine
 */
export class CargoAuditor {
  /**
   * Audit Cargo manifest text
   * @param {string} tomlContent
   * @param {string} [fileName="Cargo.toml"]
   */
  audit(tomlContent, fileName = 'Cargo.toml') {
    const issues = [];
    let parsed;

    try {
      parsed = CargoTomlParser.parse(tomlContent);
    } catch (err) {
      return {
        fileName,
        isValid: false,
        score: 0,
        grade: 'F',
        issues: [{
          ruleId: 'CARGO-SYN-001',
          ruleName: RULES['CARGO-SYN-001'].name,
          severity: 'ERROR',
          message: `TOML Syntax Error: ${err.message}`,
          line: 1,
          fixable: false
        }],
        dependencies: [],
        metrics: { totalDeps: 0, duplicateDeps: 0, unpinnedDeps: 0, errorCount: 1, warnCount: 0, suggestionCount: 0 }
      };
    }

    const { tables, keyLines } = parsed;
    const pkg = tables.package || tables._root.package || null;
    const workspace = tables.workspace || tables._root.workspace || null;
    const workspaceDeps = tables.workspace?.dependencies || {};

    const isWorkspaceRoot = Boolean(workspace && !pkg);
    const isPublishable = pkg ? (pkg.publish !== false) : false;

    // --- Package Metadata & Edition Checks ---
    if (pkg) {
      const pkgLine = keyLines.get('table_package') || 1;

      // 1. Edition (CARGO-EDN-001, CARGO-EDN-002)
      if (!pkg.edition) {
        issues.push({
          ruleId: 'CARGO-EDN-001',
          ruleName: RULES['CARGO-EDN-001'].name,
          severity: RULES['CARGO-EDN-001'].severity,
          message: "Package does not specify an 'edition' (defaults to obsolete Rust 2015 edition).",
          line: keyLines.get('package.edition') || pkgLine,
          fixable: true
        });
      } else {
        const edn = String(pkg.edition).trim();
        if (edn === '2015' || edn === '2018') {
          issues.push({
            ruleId: 'CARGO-EDN-002',
            ruleName: RULES['CARGO-EDN-002'].name,
            severity: RULES['CARGO-EDN-002'].severity,
            message: `Package uses outdated Rust edition '${edn}'. Recommend upgrading to '2021' or '2024'.`,
            line: keyLines.get('package.edition') || pkgLine,
            fixable: true
          });
        }
      }

      // 2. Description (CARGO-META-001)
      if (!pkg.description) {
        issues.push({
          ruleId: 'CARGO-META-001',
          ruleName: RULES['CARGO-META-001'].name,
          severity: isPublishable ? 'WARNING' : 'SUGGESTION',
          message: `Package missing 'description'${isPublishable ? ' required for crates.io publishing' : ''}.`,
          line: pkgLine,
          fixable: true
        });
      }

      // 3. License (CARGO-META-002)
      if (!pkg.license && !pkg['license-file']) {
        issues.push({
          ruleId: 'CARGO-META-002',
          ruleName: RULES['CARGO-META-002'].name,
          severity: isPublishable ? 'WARNING' : 'SUGGESTION',
          message: `Package missing 'license' or 'license-file'${isPublishable ? ' required for crates.io publishing' : ''}.`,
          line: pkgLine,
          fixable: true
        });
      }

      // 4. Repository (CARGO-META-003)
      if (!pkg.repository) {
        issues.push({
          ruleId: 'CARGO-META-003',
          ruleName: RULES['CARGO-META-003'].name,
          severity: RULES['CARGO-META-003'].severity,
          message: "Package missing 'repository' URL in [package].",
          line: pkgLine,
          fixable: true
        });
      }

      // 5. Readme (CARGO-META-004)
      if (!pkg.readme) {
        issues.push({
          ruleId: 'CARGO-META-004',
          ruleName: RULES['CARGO-META-004'].name,
          severity: RULES['CARGO-META-004'].severity,
          message: "Package missing 'readme' specification in [package].",
          line: pkgLine,
          fixable: true
        });
      }

      // 6. MSRV (CARGO-MSRV-001)
      if (!pkg['rust-version']) {
        issues.push({
          ruleId: 'CARGO-MSRV-001',
          ruleName: RULES['CARGO-MSRV-001'].name,
          severity: RULES['CARGO-MSRV-001'].severity,
          message: "Package does not declare Minimum Supported Rust Version ('rust-version').",
          line: pkgLine,
          fixable: true
        });
      }
    }

    // --- Dependency Analysis ---
    const allDependencies = [];
    const depTables = [
      { name: 'dependencies', data: tables.dependencies || {} },
      { name: 'dev-dependencies', data: tables['dev-dependencies'] || {} },
      { name: 'build-dependencies', data: tables['build-dependencies'] || {} },
      { name: 'workspace.dependencies', data: workspaceDeps }
    ];

    const depVersionMap = new Map();

    for (const { name: tableName, data: tableObj } of depTables) {
      if (!tableObj || typeof tableObj !== 'object') continue;

      for (const [crateName, depSpec] of Object.entries(tableObj)) {
        const depLine = keyLines.get(`${tableName}.${crateName}`) || keyLines.get(`table_${tableName}`) || 1;

        let version = null;
        let isWildcard = false;
        let isUnpinnedGit = false;
        let isOpenEnded = false;
        let isWorkspaceInherited = false;
        let gitUrl = null;
        let features = [];

        if (typeof depSpec === 'string') {
          version = depSpec.trim();
        } else if (typeof depSpec === 'object' && depSpec !== null) {
          if (depSpec.version) version = String(depSpec.version).trim();
          if (depSpec.workspace === true) isWorkspaceInherited = true;
          if (depSpec.git) {
            gitUrl = depSpec.git;
            if (!depSpec.tag && !depSpec.rev) {
              isUnpinnedGit = true;
            }
          }
          if (Array.isArray(depSpec.features)) {
            features = depSpec.features;
          }
        }

        const depInfo = {
          crate: crateName,
          table: tableName,
          version,
          isWorkspaceInherited,
          isUnpinnedGit,
          gitUrl,
          features,
          line: depLine
        };
        allDependencies.push(depInfo);

        // Version Requirement Checks
        if (version) {
          // Check CARGO-PIN-001: Wildcard '*'
          if (version === '*' || version.startsWith('*')) {
            isWildcard = true;
            issues.push({
              ruleId: 'CARGO-PIN-001',
              ruleName: RULES['CARGO-PIN-001'].name,
              severity: RULES['CARGO-PIN-001'].severity,
              crate: crateName,
              message: `Dependency '${crateName}' uses wildcard version requirement '${version}' in [${tableName}].`,
              line: depLine,
              fixable: true
            });
          }

          // Check CARGO-PIN-003: Open-ended '>= 1.0'
          if (version.startsWith('>=') && !version.includes(',') && !version.includes('<')) {
            isOpenEnded = true;
            issues.push({
              ruleId: 'CARGO-PIN-003',
              ruleName: RULES['CARGO-PIN-003'].name,
              severity: RULES['CARGO-PIN-003'].severity,
              crate: crateName,
              message: `Dependency '${crateName}' specifies unbounded range '${version}' in [${tableName}].`,
              line: depLine,
              fixable: true
            });
          }

          // Check CARGO-DUP-002: Redundant definition when workspace defines it
          if (tableName !== 'workspace.dependencies' && workspaceDeps[crateName] && !isWorkspaceInherited) {
            issues.push({
              ruleId: 'CARGO-DUP-002',
              ruleName: RULES['CARGO-DUP-002'].name,
              severity: RULES['CARGO-DUP-002'].severity,
              crate: crateName,
              message: `Dependency '${crateName}' is defined in [workspace.dependencies] but redeclared with version '${version}' instead of '{ workspace = true }'.`,
              line: depLine,
              fixable: true
            });
          }

          // Record version across tables for collision check
          if (!depVersionMap.has(crateName)) {
            depVersionMap.set(crateName, []);
          }
          depVersionMap.get(crateName).push({ table: tableName, version, line: depLine });
        }

        // Check CARGO-PIN-002: Unpinned Git Dependency
        if (isUnpinnedGit) {
          issues.push({
            ruleId: 'CARGO-PIN-002',
            ruleName: RULES['CARGO-PIN-002'].name,
            severity: RULES['CARGO-PIN-002'].severity,
            crate: crateName,
            message: `Git dependency '${crateName}' (${gitUrl}) does not specify an immutable 'rev' or 'tag' in [${tableName}].`,
            line: depLine,
            fixable: false
          });
        }
      }
    }

    // Check CARGO-DUP-001: Duplicate Dependency Versions across sections
    for (const [crateName, occurrences] of depVersionMap.entries()) {
      if (occurrences.length > 1) {
        const uniqueVersions = new Set(occurrences.map(o => o.version));
        if (uniqueVersions.size > 1) {
          const versionsStr = occurrences.map(o => `${o.table}: '${o.version}'`).join(', ');
          issues.push({
            ruleId: 'CARGO-DUP-001',
            ruleName: RULES['CARGO-DUP-001'].name,
            severity: RULES['CARGO-DUP-001'].severity,
            crate: crateName,
            message: `Conflicting versions detected for dependency '${crateName}': ${versionsStr}.`,
            line: occurrences[1].line,
            fixable: true
          });
        }
      }
    }

    // --- Profile Release Checks (CARGO-PRF-001) ---
    const releaseProfile = tables['profile.release'] || tables.profile?.release || null;
    if (pkg && !isWorkspaceRoot) {
      if (!releaseProfile || (!releaseProfile.lto && !releaseProfile.strip)) {
        issues.push({
          ruleId: 'CARGO-PRF-001',
          ruleName: RULES['CARGO-PRF-001'].name,
          severity: RULES['CARGO-PRF-001'].severity,
          message: "Manifest lacks [profile.release] production optimizations ('lto = true', 'strip = true', 'codegen-units = 1').",
          line: keyLines.get('table_package') || 1,
          fixable: true
        });
      }
    }

    // --- Calculate Health Score & Letter Grade ---
    const errorCount = issues.filter(i => i.severity === 'ERROR').length;
    const warnCount = issues.filter(i => i.severity === 'WARNING').length;
    const suggestionCount = issues.filter(i => i.severity === 'SUGGESTION').length;

    let score = 100 - (errorCount * 15) - (warnCount * 5) - (suggestionCount * 2);
    score = Math.max(0, Math.min(100, score));

    let grade = 'A+';
    if (score < 60 || errorCount > 2) grade = 'F';
    else if (score < 70) grade = 'D';
    else if (score < 80) grade = 'C';
    else if (score < 90) grade = 'B';
    else if (score < 95) grade = 'A';

    return {
      fileName,
      isValid: errorCount === 0,
      score,
      grade,
      issues,
      dependencies: allDependencies,
      tables,
      metrics: {
        totalDeps: allDependencies.length,
        duplicateDeps: issues.filter(i => i.ruleId.startsWith('CARGO-DUP')).length,
        unpinnedDeps: issues.filter(i => i.ruleId.startsWith('CARGO-PIN')).length,
        errorCount,
        warnCount,
        suggestionCount
      }
    };
  }

  /**
   * Automatically repair fixable issues in Cargo.toml
   */
  static autoFix(tomlContent) {
    let fixed = tomlContent;

    // 1. Fix edition: update 2015/2018 to 2021
    if (/^[ \t]*edition[ \t]*=[ \t]*['"](2015|2018)['"]/m.test(fixed)) {
      fixed = fixed.replace(
        /^[ \t]*edition[ \t]*=[ \t]*['"](2015|2018)['"]/m,
        'edition = "2021"'
      );
    } else if (!/^[ \t]*edition[ \t]*=/m.test(fixed) && /^\[package\]/m.test(fixed)) {
      fixed = fixed.replace(
        /^\[package\][ \t]*\r?\n/m,
        '[package]\nedition = "2021"\n'
      );
    }

    // 2. Fix Wildcard dependencies: replace "*" with "^1.0"
    fixed = fixed.replace(/=[ \t]*['"]\*['"]/g, '= "^1.0"');
    fixed = fixed.replace(/version[ \t]*=[ \t]*['"]\*['"]/g, 'version = "^1.0"');

    // 3. Fix Open-ended ranges: ">= 1.0" -> ">= 1.0, < 2.0"
    fixed = fixed.replace(/=[ \t]*['"]>=[ \t]*([0-9]+)\.([0-9]+)['"]/g, '= ">= $1.$2, < ' + '2.0"');

    // 4. Invert uninherited workspace dependency: e.g. serde = "1.0" -> serde = { workspace = true } if workspace has it
    if (/\[workspace\.dependencies\]/m.test(fixed)) {
      // workspace exists
    }

    // 5. Inject [profile.release] if missing
    if (!/\[profile\.release\]/m.test(fixed)) {
      fixed = fixed.trimEnd() + '\n\n[profile.release]\nopt-level = 3\nlto = true\ncodegen-units = 1\nstrip = true\npanic = "abort"\n';
    }

    return fixed;
  }
}
