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
const pending = {number: 77, html_url: `https://github.com/${owner}/${repo}/pull/77`};
const published = {tag_name: 'v3.1.0', html_url: `https://github.com/${owner}/${repo}/releases/tag/v3.1.0`};

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

test('published release bodies are matched the same way', () => {
  const body = `### Features\n\n* redesign logging ([#61](https://github.com/${owner}/${repo}/issues/61)) ([4b3a0bf](https://github.com/${owner}/${repo}/commit/4b3a0bfb5379))\n* no link to a commit ([#5](https://github.com/${owner}/${repo}/issues/5))`;
  const lines = notify.releaseBodyLines(body);
  assert.deepEqual([...notify.includedNumbers(lines, owner, repo, -1)], [61]);
  assert.equal(notify.confirmsCommit(lines, 61, '4b3a0bfb53796ece65aa1c5315f569fc8a13c6a1', owner, repo), true);
  assert.deepEqual(notify.releaseBodyLines(''), ['+']);
});

test('credits thank each human PR author once, skipping bots', () => {
  const credits = new Map();
  notify.addCredit(credits, {number: 79, user: {login: 'NatesHonor', type: 'User'}});
  notify.addCredit(credits, {number: 75, user: {login: 'NatesHonor', type: 'User'}});
  notify.addCredit(credits, {number: 75, user: {login: 'NatesHonor', type: 'User'}});
  notify.addCredit(credits, {number: 74, user: {login: 'dependabot[bot]', type: 'Bot'}});
  notify.addCredit(credits, {number: 70, user: {login: 'helper', type: 'User'}});
  const section = notify.creditsSection(credits);
  assert.match(section, /Thanks to @NatesHonor for #75, #79/);
  assert.match(section, /Thanks to @helper for #70/);
  assert.doesNotMatch(section, /dependabot/);
  assert.equal(notify.creditsSection(new Map()), '');
  assert.match(notify.creditsComment('v3.2.0', credits), /contributed to \*\*v3\.2\.0\*\*/);
});

test('credits block in a release body is replaced, not duplicated', () => {
  const credits = new Map([['NatesHonor', [79]]]);
  const once = notify.withCredits('### Bug Fixes\n\n* fix thing', credits);
  const twice = notify.withCredits(once, credits);
  assert.equal(once, twice);
  assert.equal(once.split('### Credits').length, 2);
  assert.match(once, /^### Bug Fixes/);
  // The bot's own block never counts as release notes.
  assert.ok(!notify.releaseBodyLines(once).some(line => line.includes('Thanks to')));
});

test('comments link the right release and version', () => {
  assert.match(notify.message('v3.2.0', pending), /#77 — Release v3\.2\.0/);
  assert.match(notify.message('v3.2.0', pending), /mission-auto-release-bot:pending-release/);
  assert.match(notify.releasedMessage('v3.1.0', published), /\*\*Released!\*\*/);
  assert.match(notify.releasedMessage('v3.1.0', published), /releases\/tag\/v3\.1\.0/);
});
