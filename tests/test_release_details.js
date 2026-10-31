'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const enrich = require('../.github/scripts/enrich-release-notes.cjs');
const notify = require('../.github/scripts/notify-release-prs.cjs');

const owner = 'NatesHonor';
const repo = 'MissionchiefBot-X';
const url = `https://github.com/${owner}/${repo}`;
const squash = 'aaaaaaa111111111111111111111111111111111';
const missedSha = 'bbbbbbb222222222222222222222222222222222';
const direct = 'ccccccc333333333333333333333333333333333';
const second = 'ddddddd444444444444444444444444444444444';

const entry83 = `* refine logging ([#83](${url}/issues/83)) ([aaaaaaa](${url}/commit/${squash}))`;
const entry85 = `* **ci:** tighten tokens ([#85](${url}/issues/85)) ([ddddddd](${url}/commit/${second}))`;

const changelog = [
  '# Changelog',
  '',
  `## [3.3.0](${url}/compare/v3.2.0...v3.3.0) (2026-10-30)`,
  '',
  '',
  '### Bug Fixes',
  '',
  entry85,
  entry83,
  '',
  `## [3.2.0](${url}/compare/v3.1.0...v3.2.0) (2026-10-21)`,
  '',
  `* older entry ([#70](${url}/issues/70)) ([aaaaaaa](${url}/commit/${squash}))`,
  '',
].join('\n');

const people = new Map([
  [squash, {author: '@NatesHonor', credits: ['Bob (reported on Discord)']}],
  [second, {author: '@helper', credits: []}],
  [missedSha, {author: '@NatesHonor', credits: []}],
  [direct, {author: '@pusher', credits: []}],
]);
const missed = [
  {sha: missedSha, number: 84, subject: 'Update README'},
  {sha: direct, subject: 'tweak docs'},
];

test('entries end with the author and any credited names', () => {
  const updated = enrich.withDetails(changelog, 'v3.3.0', '', people);
  assert.ok(updated.includes(`${entry83} @NatesHonor (credit: Bob (reported on Discord))`));
  assert.ok(updated.includes(`${entry85} @helper`));
  assert.ok(!updated.includes('Pull Request Commits'));
  // Older releases are left alone.
  assert.ok(updated.includes(`* older entry ([#70](${url}/issues/70)) ([aaaaaaa](${url}/commit/${squash}))\n`));
});

test('running again replaces the attribution instead of adding another', () => {
  const once = enrich.withDetails(changelog, 'v3.3.0', '', people);
  assert.equal(enrich.withDetails(once, 'v3.3.0', '', people), once);
  const changed = new Map(people);
  changed.set(squash, {author: '@NatesHonor', credits: []});
  const again = enrich.withDetails(once, 'v3.3.0', '', changed);
  assert.ok(again.includes(`${entry83} @NatesHonor\n`));
  assert.ok(!again.includes('Bob'));
});

test('credits section of a PR description is read', () => {
  const body = [
    '## Summary', '', 'Fixes the crash.', '',
    '## Credits', '',
    '<!-- Credit anyone who helped, such as someone who reported the bug on Discord. -->',
    '- Bob (reported on Discord)', '* @alice', '1. Carol', '- bob (reported on Discord)', '',
    '## Testing', '', '- [x] Unit tests pass locally',
  ].join('\r\n');
  assert.deepEqual(enrich.creditsFrom(body), ['Bob (reported on Discord)', '@alice', 'Carol']);
  assert.deepEqual(enrich.creditsFrom('Fixes it.\n\n**Credits:** Dave, Erin'), ['Dave', 'Erin']);
  assert.deepEqual(enrich.creditsFrom('## Credits\n\n<!-- placeholder -->\n\nNone\n'), []);
  assert.deepEqual(enrich.creditsFrom('### Credit\nFrank'), ['Frank']);
  assert.deepEqual(enrich.creditsFrom(null), []);
});

test('attribution skips a credit that repeats the author and escapes names', () => {
  assert.equal(enrich.attribution({author: '@NatesHonor', credits: ['NatesHonor']}), '@NatesHonor');
  assert.equal(enrich.attribution({author: '@a', credits: ['<b>']}), '@a (credit: \\<b\\>)');
  assert.equal(enrich.attribution({author: null, credits: ['Bob']}), '(credit: Bob)');
  assert.equal(enrich.attribution(null), '');
  assert.equal(enrich.mention({login: 'dependabot[bot]'}), '@dependabot');
  assert.equal(enrich.mention(null), null);
});

test('missed commits are listed flat with their author', () => {
  const block = enrich.detailsBlock({owner, repo, missed, people});
  assert.ok(block.startsWith(enrich.START) && block.endsWith(enrich.END));
  assert.match(block, /### Other Changes/);
  assert.ok(block.includes(`* Update README ([#84](${url}/issues/84)) ([bbbbbbb](${url}/commit/${missedSha})) @NatesHonor`));
  assert.ok(block.includes(`* tweak docs ([ccccccc](${url}/commit/${direct})) @pusher`));
  assert.equal(enrich.detailsBlock({owner, repo, missed: [], people}), '');
});

test('block goes at the end of the version section and is replaced, not duplicated', () => {
  const block = enrich.detailsBlock({owner, repo, missed, people});
  const once = enrich.withDetails(changelog, 'v3.3.0', block, people);
  const twice = enrich.withDetails(once, 'v3.3.0', block, people);
  assert.equal(once, twice);
  assert.equal(once.split(enrich.START).length, 2);
  assert.ok(once.indexOf(enrich.END) < once.indexOf('## [3.2.0]'));
  assert.ok(once.indexOf('### Bug Fixes') < once.indexOf(enrich.START));
  assert.equal(enrich.withDetails(changelog, 'v9.9.9', block, people), null);
});

test('CRLF changelogs keep their line endings', () => {
  const crlf = changelog.replace(/\n/g, '\r\n');
  const updated = enrich.withDetails(crlf, 'v3.3.0', enrich.detailsBlock({owner, repo, missed, people}), people);
  assert.ok(!/[^\r]\n/.test(updated));
  assert.ok(updated.includes('@NatesHonor (credit: Bob'));
});

test('release PR body footer ends the section', () => {
  const body = `:robot: I have created a release *beep* *boop*\n---\n\n\n## [3.3.0](${url}/compare/v3.2.0...v3.3.0) (2026-10-30)\n\n\n### Bug Fixes\n\n${entry83}\n\n---\nThis PR was generated with Release Please.`;
  const block = enrich.detailsBlock({owner, repo, missed, people});
  const updated = enrich.withDetails(body, 'v3.3.0', block, people);
  assert.ok(updated.includes(`${entry83} @NatesHonor`));
  assert.ok(updated.indexOf(enrich.END) < updated.lastIndexOf('---'));
  assert.ok(updated.endsWith('This PR was generated with Release Please.'));
  assert.equal(enrich.withDetails(updated, 'v3.3.0', block, people), updated);
});

test('generated notes exclude the bot block when checking what was missed', () => {
  const withBlock = enrich.withDetails(changelog, 'v3.3.0', enrich.detailsBlock({owner, repo, missed, people}), people);
  const shas = enrich.referencedShas(enrich.sectionLines(withBlock, 'v3.3.0'));
  assert.ok(enrich.isReferenced(shas, squash));
  assert.ok(!enrich.isReferenced(shas, missedSha));
  assert.ok(!enrich.isReferenced(shas, direct));
});

test('squash suffix is removed from subjects', () => {
  assert.equal(enrich.stripPrSuffix('fix: thing (#83)', 83), 'fix: thing');
  assert.equal(enrich.stripPrSuffix('fix: thing (#83)', undefined), 'fix: thing (#83)');
  assert.equal(enrich.subjectOf('feat: a\n\nbody'), 'feat: a');
});

test('collect finds authors, credits and commits missing from the notes', async () => {
  const pr83 = {number: 83, title: 'fix: refine logging', merged_at: 'x', base: {ref: 'main'},
    user: {login: 'NatesHonor'}, body: '## Credits\n- Bob (reported on Discord)',
    merge_commit_sha: squash, head: {ref: 'fix/x', repo: {full_name: `${owner}/${repo}`}}};
  const pr84 = {number: 84, title: 'Update README', merged_at: 'x', base: {ref: 'main'},
    user: {login: 'helper'}, body: null,
    merge_commit_sha: missedSha, head: {ref: 'docs', repo: {full_name: `${owner}/${repo}`}}};
  const mainCommits = [
    {sha: squash, parents: [{}], author: {login: 'someone-else'}, commit: {message: 'fix: refine logging (#83)'}},
    {sha: missedSha, parents: [{}], author: {login: 'helper'}, commit: {message: 'Update README (#84)'}},
    {sha: direct, parents: [{}], author: {login: 'pusher'}, commit: {message: 'tweak docs'}},
    {sha: 'fffffff666666666666666666666666666666666', parents: [{}, {}], commit: {message: 'Merge branch'}},
  ];
  const github = {
    rest: {
      repos: {
        compareCommitsWithBasehead: async () => ({data: {commits: mainCommits, total_commits: mainCommits.length}}),
        listPullRequestsAssociatedWithCommit: async ({commit_sha}) =>
          ({data: commit_sha === squash ? [pr83] : commit_sha === missedSha ? [pr84] : []}),
      },
    },
  };
  const notes = enrich.sectionLines(changelog, 'v3.3.0');
  const result = await enrich.collect({github, owner, repo, base: 'main', since: 'v3.2.0', notes});
  assert.deepEqual(result.people.get(squash), {author: '@NatesHonor', credits: ['Bob (reported on Discord)']});
  assert.deepEqual(result.people.get(missedSha), {author: '@helper', credits: []});
  assert.deepEqual(result.people.get(direct), {author: '@pusher', credits: []});
  assert.deepEqual(result.missed.map(commit => commit.sha), [missedSha, direct]);
  assert.equal(result.missed[0].subject, 'Update README');
  assert.equal(result.missed[0].number, 84);
});

test('release notifier still finds PRs in the credited notes', () => {
  const block = enrich.detailsBlock({owner, repo, missed, people});
  const lines = notify.releaseBodyLines(enrich.withDetails(changelog, 'v3.3.0', block, people));
  const numbers = notify.includedNumbers(lines, owner, repo, -1);
  assert.ok(numbers.has(83));
  assert.ok(numbers.has(84));
  assert.ok(numbers.has(85));
  assert.ok(notify.confirmsCommit(lines, 83, squash, owner, repo));
});
