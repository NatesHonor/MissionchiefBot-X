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

const changelog = [
  '# Changelog',
  '',
  `## [3.3.0](${url}/compare/v3.2.0...v3.3.0) (2026-10-30)`,
  '',
  '',
  '### Bug Fixes',
  '',
  `* refine logging ([#83](${url}/issues/83)) ([aaaaaaa](${url}/commit/${squash}))`,
  '',
  `## [3.2.0](${url}/compare/v3.1.0...v3.2.0) (2026-10-21)`,
  '',
  '* older entry',
  '',
].join('\n');

const prs = [{number: 83, title: 'fix: refine logging', commits: [
  {sha: 'ddddddd444444444444444444444444444444444', subject: 'fix: tidy exit messages'},
  {sha: 'eeeeeee555555555555555555555555555555555', subject: 'fix: log <level> [debug]'},
]}];
const missed = [
  {sha: missedSha, number: 84, subject: 'Update README'},
  {sha: direct, subject: 'tweak docs'},
];

test('block lists PR commits and missed commits with links', () => {
  const block = enrich.detailsBlock({owner, repo, prs, missed});
  assert.ok(block.startsWith(enrich.START) && block.endsWith(enrich.END));
  assert.match(block, /### Pull Request Commits/);
  assert.match(block, new RegExp(`\\* \\[#83\\]\\(${url}/issues/83\\) fix: refine logging`));
  assert.match(block, /  \* fix: tidy exit messages \(\[ddddddd\]/);
  assert.match(block, /fix: log \\<level\\> \\\[debug\\\]/);
  assert.match(block, /### Other Changes/);
  assert.match(block, /\* Update README \(\[#84\]\(.*\/issues\/84\)\) \(\[bbbbbbb\]/);
  assert.match(block, /\* tweak docs \(\[ccccccc\]/);
  assert.equal(enrich.detailsBlock({owner, repo, prs: [], missed: []}), '');
});

test('block goes at the end of the version section and is replaced, not duplicated', () => {
  const block = enrich.detailsBlock({owner, repo, prs, missed});
  const once = enrich.withDetails(changelog, 'v3.3.0', block);
  const twice = enrich.withDetails(once, 'v3.3.0', block);
  assert.equal(once, twice);
  assert.equal(once.split(enrich.START).length, 2);
  assert.ok(once.indexOf(enrich.END) < once.indexOf('## [3.2.0]'));
  assert.ok(once.indexOf('### Bug Fixes') < once.indexOf(enrich.START));
  // Removing the block restores the original notes.
  assert.equal(enrich.withDetails(once, 'v3.3.0', ''), changelog);
  assert.equal(enrich.withDetails(changelog, 'v9.9.9', block), null);
});

test('CRLF changelogs keep their line endings', () => {
  const crlf = changelog.replace(/\n/g, '\r\n');
  const updated = enrich.withDetails(crlf, 'v3.3.0', enrich.detailsBlock({owner, repo, prs, missed}));
  assert.ok(!/[^\r]\n/.test(updated));
});

test('release PR body footer ends the section', () => {
  const body = `:robot: I have created a release *beep* *boop*\n---\n\n\n## [3.3.0](${url}/compare/v3.2.0...v3.3.0) (2026-10-30)\n\n\n### Bug Fixes\n\n* refine logging\n\n---\nThis PR was generated with Release Please.`;
  const block = enrich.detailsBlock({owner, repo, prs, missed});
  const updated = enrich.withDetails(body, 'v3.3.0', block);
  assert.ok(updated.indexOf(enrich.END) < updated.lastIndexOf('---'));
  assert.ok(updated.endsWith('This PR was generated with Release Please.'));
  assert.equal(enrich.withDetails(updated, 'v3.3.0', block), updated);
});

test('generated notes exclude the bot block when checking what was missed', () => {
  const withBlock = enrich.withDetails(changelog, 'v3.3.0', enrich.detailsBlock({owner, repo, prs, missed}));
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

test('collect finds PR commits and commits missing from the notes', async () => {
  const pr83 = {number: 83, title: 'fix: refine logging', merged_at: 'x', base: {ref: 'main'},
    merge_commit_sha: squash, head: {ref: 'fix/x', repo: {full_name: `${owner}/${repo}`}}};
  const pr84 = {number: 84, title: 'Update README', merged_at: 'x', base: {ref: 'main'},
    merge_commit_sha: missedSha, head: {ref: 'docs', repo: {full_name: `${owner}/${repo}`}}};
  const mainCommits = [
    {sha: squash, parents: [{}], commit: {message: 'fix: refine logging (#83)'}},
    {sha: missedSha, parents: [{}], commit: {message: 'Update README (#84)'}},
    {sha: direct, parents: [{}], commit: {message: 'tweak docs'}},
    {sha: 'fffffff666666666666666666666666666666666', parents: [{}, {}], commit: {message: 'Merge branch'}},
  ];
  const github = {
    paginate: async (fn, params) => fn(params),
    rest: {
      repos: {
        compareCommitsWithBasehead: async () => ({data: {commits: mainCommits, total_commits: mainCommits.length}}),
        listPullRequestsAssociatedWithCommit: async ({commit_sha}) =>
          ({data: commit_sha === squash ? [pr83] : commit_sha === missedSha ? [pr84] : []}),
      },
      pulls: {
        listCommits: async ({pull_number}) => pull_number === 83
          ? [{sha: 'ddddddd444444444444444444444444444444444', parents: [{}], commit: {message: 'fix: tidy exit messages'}}]
          : [{sha: '9999999777777777777777777777777777777777', parents: [{}], commit: {message: 'docs: readme'}}],
      },
    },
  };
  const notes = enrich.sectionLines(changelog, 'v3.3.0');
  const result = await enrich.collect({github, owner, repo, base: 'main', since: 'v3.2.0', notes});
  assert.deepEqual(result.prs.map(pr => pr.number), [83, 84]);
  assert.equal(result.prs[0].commits[0].subject, 'fix: tidy exit messages');
  assert.deepEqual(result.missed.map(commit => commit.sha), [missedSha, direct]);
  assert.equal(result.missed[0].subject, 'Update README');
  assert.equal(result.missed[0].number, 84);
});

test('release notifier still finds PRs in the enriched notes', () => {
  const block = enrich.detailsBlock({owner, repo, prs, missed});
  const lines = notify.releaseBodyLines(enrich.withDetails(changelog, 'v3.3.0', block));
  const numbers = notify.includedNumbers(lines, owner, repo, -1);
  assert.ok(numbers.has(83));
  assert.ok(numbers.has(84));
});
