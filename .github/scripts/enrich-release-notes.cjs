'use strict';

// Adds detail to the pending Release Please PR's release notes:
//   * "Pull Request Commits": every merged PR since the last release, with
//     the individual commits it contained (squash merges hide these).
//   * "Other Changes": commits on the default branch since the last release
//     that the generated notes do not mention (for example commits Release
//     Please could not parse), linked to their PR when there is one.
// The block is written to both CHANGELOG.md on the release branch and the
// release PR body, because Release Please builds the GitHub release from the
// PR body. Release Please rewrites both on every run, so this runs after it
// each time and replaces its own block rather than appending a second one.

const {releaseVersion} = require('./notify-release-prs.cjs');

const START = '<!-- mission-auto-release-bot:release-details:start -->';
const END = '<!-- mission-auto-release-bot:release-details:end -->';
const RELEASE_COMMIT = /^chore(\([^)]*\))?: release\b/i;

function subjectOf(message) {
  return (message || '').split(/\r?\n/)[0].trim();
}

// Squash commits end with " (#123)"; the PR link is added separately.
function stripPrSuffix(subject, number) {
  return number ? subject.replace(new RegExp(`\\s*\\(#${escapeRegExp(String(number))}\\)$`), '') : subject;
}

// Keep commit subjects from breaking links or being read as HTML.
function escapeMarkdown(text) {
  return text.replace(/([\\[\]<>])/g, '\\$1');
}

function escapeRegExp(text) {
  return text.replace(/[\\^$.*+?()[\]{}|]/g, '\\$&');
}

function commitLink(owner, repo, sha) {
  return `[${sha.slice(0, 7)}](https://github.com/${owner}/${repo}/commit/${sha})`;
}

function prLink(owner, repo, number) {
  return `[#${number}](https://github.com/${owner}/${repo}/issues/${number})`;
}

function referencedShas(lines) {
  const shas = new Set();
  for (const line of lines) {
    for (const match of line.matchAll(/\/commit\/([a-f0-9]{7,40})/gi)) shas.add(match[1].toLowerCase());
  }
  return shas;
}

function isReferenced(shas, sha) {
  const full = sha.toLowerCase();
  for (const short of shas) if (full.startsWith(short)) return true;
  return false;
}

// prs: [{number, title, commits: [{sha, subject}]}]
// missed: [{sha, subject, number?}]
function detailsBlock({owner, repo, prs, missed}) {
  const parts = [];
  if (prs.length) {
    const lines = ['### Pull Request Commits', ''];
    for (const pr of prs) {
      lines.push(`* ${prLink(owner, repo, pr.number)} ${escapeMarkdown(pr.title)}`);
      for (const commit of pr.commits) {
        lines.push(`  * ${escapeMarkdown(commit.subject)} (${commitLink(owner, repo, commit.sha)})`);
      }
    }
    parts.push(lines.join('\n'));
  }
  if (missed.length) {
    const lines = ['### Other Changes', ''];
    for (const commit of missed) {
      const pr = commit.number ? ` (${prLink(owner, repo, commit.number)})` : '';
      lines.push(`* ${escapeMarkdown(commit.subject)}${pr} (${commitLink(owner, repo, commit.sha)})`);
    }
    parts.push(lines.join('\n'));
  }
  return parts.length ? `${START}\n${parts.join('\n\n')}\n${END}` : '';
}

// Line range [start, end) of the version's section. The section ends at the
// next version heading or at Release Please's PR body footer ("---").
function sectionRange(lines, version) {
  const number = escapeRegExp(version.replace(/^v/, ''));
  const heading = new RegExp(`^#{2,3} \\[v?${number}\\]`);
  const start = lines.findIndex(line => heading.test(line));
  if (start < 0) return null;
  let end = lines.findIndex((line, index) => index > start && (/^#{2,3} \[/.test(line) || /^---\s*$/.test(line)));
  if (end < 0) end = lines.length;
  return {start, end};
}

function withoutBlock(lines) {
  const result = [];
  let inside = false;
  for (const line of lines) {
    if (line.trim() === START) { inside = true; continue; }
    if (inside) { if (line.trim() === END) inside = false; continue; }
    result.push(line);
  }
  return result;
}

// The generated notes for a version, without any block added earlier.
function sectionLines(text, version) {
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n');
  const range = sectionRange(lines, version);
  return range ? withoutBlock(lines.slice(range.start, range.end)) : null;
}

// Replace (or add) the block at the end of the version's section. Returns
// null when the section cannot be found.
function withDetails(text, version, block) {
  const eol = (text || '').includes('\r\n') ? '\r\n' : '\n';
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n');
  const range = sectionRange(lines, version);
  if (!range) return null;
  const section = withoutBlock(lines.slice(range.start, range.end));
  let trailing = 0;
  while (section.length && section[section.length - 1].trim() === '') { section.pop(); trailing++; }
  const added = block ? ['', ...block.split('\n')] : [];
  // One blank line separates the section from whatever follows it.
  const gap = trailing || range.end < lines.length ? [''] : [];
  return [...lines.slice(0, range.start), ...section, ...added, ...gap, ...lines.slice(range.end)].join(eol);
}

function isReleasePr(pr, owner, repo) {
  return pr.head?.repo?.full_name === `${owner}/${repo}` && pr.head.ref.startsWith('release-please--');
}

async function commitsSince(github, owner, repo, basehead) {
  const commits = [];
  for (let page = 1; ; page++) {
    const {data} = await github.rest.repos.compareCommitsWithBasehead({owner, repo, basehead, per_page: 100, page});
    commits.push(...data.commits);
    if (data.commits.length < 100 || commits.length >= data.total_commits) break;
  }
  return commits;
}

// Gathers PRs and their commits, plus commits the generated notes missed.
async function collect({github, owner, repo, base, since, notes}) {
  const mainCommits = (await commitsSince(github, owner, repo, `${since}...${base}`))
    .filter(commit => (commit.parents || []).length < 2 && !RELEASE_COMMIT.test(subjectOf(commit.commit.message)));

  const prs = new Map();
  const prOf = new Map();
  for (const commit of mainCommits) {
    const {data: associated} = await github.rest.repos.listPullRequestsAssociatedWithCommit(
      {owner, repo, commit_sha: commit.sha});
    const merged = associated.filter(pr => pr.merged_at && pr.base.ref === base && !isReleasePr(pr, owner, repo));
    const pr = merged.find(item => item.merge_commit_sha === commit.sha) || merged[0];
    if (!pr) continue;
    prOf.set(commit.sha, pr.number);
    if (!prs.has(pr.number)) prs.set(pr.number, {number: pr.number, title: pr.title, commits: []});
  }

  for (const pr of prs.values()) {
    const commits = await github.paginate(github.rest.pulls.listCommits,
      {owner, repo, pull_number: pr.number, per_page: 100});
    pr.commits = commits
      .filter(commit => (commit.parents || []).length < 2)
      .map(commit => ({sha: commit.sha, subject: subjectOf(commit.commit.message)}));
  }

  const covered = referencedShas(notes);
  for (const pr of prs.values()) for (const commit of pr.commits) covered.add(commit.sha.toLowerCase());
  const missed = mainCommits
    .filter(commit => !isReferenced(covered, commit.sha))
    .map(commit => {
      const number = prOf.get(commit.sha);
      return {sha: commit.sha, number, subject: stripPrSuffix(subjectOf(commit.commit.message), number)};
    });

  return {prs: [...prs.values()].sort((a, b) => a.number - b.number), missed};
}

async function enrich({github, context, core}) {
  try {
    const {owner, repo} = context.repo;
    const base = context.payload.repository.default_branch;

    const open = await github.paginate(github.rest.pulls.list, {owner, repo, state: 'open', base, per_page: 100});
    const pending = open.filter(pr => isReleasePr(pr, owner, repo) &&
      pr.labels.some(label => label.name === 'autorelease: pending'));
    if (pending.length !== 1) {
      core.info(`Expected one pending Release Please PR; found ${pending.length}. Skipping release details.`);
      return;
    }
    const release = pending[0];

    const files = await github.paginate(github.rest.pulls.listFiles,
      {owner, repo, pull_number: release.number, per_page: 100});
    const version = releaseVersion(files.find(file => file.filename === '.release-please-manifest.json')?.patch);
    if (!version) { core.warning(`Unable to read version from release PR #${release.number}.`); return; }

    let latest = null;
    try {
      ({data: latest} = await github.rest.repos.getLatestRelease({owner, repo}));
    } catch (error) {
      if (error.status !== 404) throw error;
    }
    if (!latest) { core.info('No published release to compare against. Skipping release details.'); return; }

    const {data: file} = await github.rest.repos.getContent(
      {owner, repo, path: 'CHANGELOG.md', ref: release.head.ref});
    const changelog = Buffer.from(file.content, 'base64').toString('utf8');
    const notes = sectionLines(changelog, version);
    if (!notes) { core.warning(`Could not find ${version} in CHANGELOG.md on ${release.head.ref}.`); return; }

    const {prs, missed} = await collect({github, owner, repo, base, since: latest.tag_name, notes});
    const block = detailsBlock({owner, repo, prs, missed});

    const updated = withDetails(changelog, version, block);
    if (updated !== null && updated !== changelog) {
      await github.rest.repos.createOrUpdateFileContents({
        owner, repo, path: 'CHANGELOG.md', branch: release.head.ref, sha: file.sha,
        message: `chore: add pull request commits and missed changes to ${version} release notes`,
        content: Buffer.from(updated, 'utf8').toString('base64'),
      });
    }

    const body = withDetails(release.body || '', version, block);
    if (body === null) core.warning(`Could not find ${version} in the body of release PR #${release.number}.`);
    else if (body !== release.body) await github.rest.pulls.update({owner, repo, pull_number: release.number, body});

    core.info(`Release details for ${version}: ${prs.length} PR(s), ${missed.length} missed commit(s).`);
  } catch (error) {
    core.warning(`Release details skipped: ${error.message}`);
  }
}

module.exports = enrich;
module.exports.START = START;
module.exports.END = END;
module.exports.subjectOf = subjectOf;
module.exports.stripPrSuffix = stripPrSuffix;
module.exports.escapeMarkdown = escapeMarkdown;
module.exports.referencedShas = referencedShas;
module.exports.isReferenced = isReferenced;
module.exports.detailsBlock = detailsBlock;
module.exports.sectionRange = sectionRange;
module.exports.sectionLines = sectionLines;
module.exports.withDetails = withDetails;
module.exports.collect = collect;
