import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { CargoAuditor, CargoTomlParser } from '../js/cargo_auditor.js';
import { PRESET_STANDARD_BINARY, PRESET_WORKSPACE, PRESET_VULNERABLE } from '../js/samples.js';

describe('CargoAuditor', () => {
  const auditor = new CargoAuditor();

  it('should audit clean standard binary with A+ score and 0 errors', () => {
    const res = auditor.audit(PRESET_STANDARD_BINARY);
    assert.equal(res.isValid, true);
    assert.equal(res.metrics.errorCount, 0);
    assert.equal(res.score, 100);
    assert.equal(res.grade, 'A+');
    assert.equal(res.dependencies.length, 9);
  });

  it('should detect vulnerabilities in vulnerable manifest', () => {
    const res = auditor.audit(PRESET_VULNERABLE);
    assert.equal(res.isValid, false);
    assert.ok(res.metrics.errorCount >= 2); // rand = "*" and test-log = "*"
    assert.ok(res.score < 70);

    const ruleIds = res.issues.map(i => i.ruleId);
    assert.ok(ruleIds.includes('CARGO-PIN-001'), 'Must flag wildcard dependency (CARGO-PIN-001)');
    assert.ok(ruleIds.includes('CARGO-PIN-002'), 'Must flag unpinned git dependency (CARGO-PIN-002)');
    assert.ok(ruleIds.includes('CARGO-PIN-003'), 'Must flag open-ended inequality (CARGO-PIN-003)');
    assert.ok(ruleIds.includes('CARGO-EDN-002'), 'Must flag outdated edition 2015 (CARGO-EDN-002)');
    assert.ok(ruleIds.includes('CARGO-META-001'), 'Must flag missing description (CARGO-META-001)');
    assert.ok(ruleIds.includes('CARGO-META-002'), 'Must flag missing license (CARGO-META-002)');
    assert.ok(ruleIds.includes('CARGO-DUP-001'), 'Must flag mismatched duplicate serde version (CARGO-DUP-001)');
    assert.ok(ruleIds.includes('CARGO-PRF-001'), 'Must flag missing profile.release (CARGO-PRF-001)');
  });

  it('should audit workspace root manifests', () => {
    const res = auditor.audit(PRESET_WORKSPACE);
    assert.equal(res.isValid, true);
    assert.ok(res.tables.workspace);
    assert.ok(res.dependencies.some(d => d.table === 'workspace.dependencies'));
  });

  it('should auto-fix outdated edition and wildcard dependencies', () => {
    const toml = `[package]
name = "foo"
version = "0.1.0"
edition = "2015"

[dependencies]
serde = "*"
`;
    const fixed = CargoAuditor.autoFix(toml);
    assert.ok(fixed.includes('edition = "2021"'), 'Must upgrade edition to 2021');
    assert.ok(!fixed.includes('serde = "*"'), 'Must eliminate wildcard dependency');
    assert.ok(fixed.includes('serde = "^1.0"'), 'Must replace with pinned semver');
    assert.ok(fixed.includes('[profile.release]'), 'Must inject profile.release');
  });

  it('should reject invalid TOML with CARGO-SYN-001', () => {
    const res = auditor.audit('');
    assert.equal(res.isValid, false);
    assert.equal(res.issues[0].ruleId, 'CARGO-SYN-001');
  });
});
