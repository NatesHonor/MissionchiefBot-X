'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const notify = require('../.github/scripts/notify-release-prs.cjs');

const owner = 'NatesHonor';
const repo = 'MissionchiefBot-X';
const sha = 'e155a249fe8f077b8fc0d3d52b66371d31b66cd2';
const diff = `diff --git a/CHANGELOG.md b/CHANGELOG.md
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -1,3 +1,6 @@
+## [3.2.0](https://github.com/${owner}/${repo}/compare/v3.1.0...v3.2.0)
+* fix release ([#79](https://github.com/${owner}/${repo}/issues/79)) ([e155a24](https://github.com/${owner}/${repo}/commit/e155a249))
+* mention ([#12](https://github.com/${owner}/${repo}/issues/12))
 ## [3.1.0](old)
`;
const release = {number: 77, html_url: `https://github.com/${owner}/${repo}/pull/77`};

test('version comes from Release Please manifest diff', () => {
  assert.equal(notify.releaseVersion('@@ -1 +1 @@\n-  ".": "3.1.0"\n+  ".": "3.2.0"'), 'v3.2.0');
  assert.equal(notify.releaseVersion(''), null);
});
test('only added lines in the actual version section qualify', () => {
  const lines = notify.releaseNotesFromDiff(diff, 'v3.2.0');
  assert.equal(lines.length, 3);
  assert.deepEqual([...notify.includedNumbers(lines, owner, repo, 77)], [79]);
  assert.equal(notify.confirmsCommit(lines, 79, sha, owner, repo), true);
  assert.equal(notify.confirmsCommit(lines, 12, sha, owner, repo), false);
  assert.equal(notify.confirmsCommit(lines, 79, 'abcdef0123456789', owner, repo), false);
  assert.equal(notify.releaseNotesFromDiff(diff, 'v3.3.0'), null);
});
test('comment links the right release and version', () => {
  assert.match(notify.message('v3.2.0', release), /#77 — Release v3\.2\.0/);
  assert.match(notify.message('v3.2.0', release), /mission-auto-release-bot:pending-release/);
});
