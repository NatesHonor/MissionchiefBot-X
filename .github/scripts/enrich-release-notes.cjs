'use strict';

// Polishes the pending Release Please PR's release notes:
//   * Every entry ends with "@author" (the PR author, or the commit author for
//     direct pushes), followed by any names listed in the PR description's
//     "Credits" section. This credits people without a GitHub account, for
//     example someone on Discord who reported the bug.
//   * "Other Changes": commits on the default branch since the last release
//     that the generated notes do not mention (for example commits Release
//     Please could not parse), in the same flat format.
// Both CHANGELOG.md on the release branch and the release PR body are updated,
// because Release Please builds the GitHub release from the PR body. Release
// Please rewrites both on every run, so this runs after it each time. Running
// it again on notes it has already changed gives the same result.

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

// "@login" for a GitHub user. Bot accounts lose their "[bot]" suffix.
function mention(user) {
  return user?.login ? `@${user.login.replace(/\[bot\]$/i, '')}` : null;
}

const NO_CREDIT = /^(?:none|n\/a|-+)$/i;

// Names from a "Credits" section of a PR description, one per line:
//   ## Credits
//   - Bob (reported it on Discord)
//   - @alice
// or from a single line such as "Credits: Bob, Alice". HTML comments (the
// PR template's placeholder) and "None" are ignored.
function creditsFrom(body) {
  const names = [];
  let inSection = false;
  const text = (body || '').replace(/<!--[\s\S]*?-->/g, '');
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(/\*\*/g, '').trim();
    const heading = line.match(/^#{1,6}\s+(.*?)[\s#]*$/);
    if (heading) { inSection = /^credits?\b/i.test(heading[1]); continue; }
    if (/^-{3,}$/.test(line)) { inSection = false; continue; }
    const inline = line.match(/^(?:[-*+]\s+)?credits?\s*:\s*(.+)$/i);
    if (inline) { names.push(...inline[1].split(',')); continue; }
    if (inSection) names.push(line.replace(/^(?:[-*+]|\d+[.)])\s+/, ''));
  }
  const seen = new Set();
  return names.map(name => name.trim()).filter(name => {
    const key = name.toLowerCase();
    if (!name || NO_CREDIT.test(name) || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

// "@author (credit: Bob, Alice)", or '' when nobody is known.
function attribution(person) {
  if (!person) return '';
  const author = person.author || '';
  const same = name => name.replace(/^@/, '').toLowerCase() === author.replace(/^@/, '').toLowerCase();
  const credits = (person.credits || []).filter(name => !same(name)).map(escapeMarkdown);
  if (!credits.length) return author;
  return `${author ? `${author} ` : ''}(credit: ${credits.join(', ')})`;
}

// people: Map of full lowercase commit SHA -> {author, credits}.
function personFor(people, sha) {
  const short = sha.toLowerCase();
  for (const [full, person] of people) if (full.startsWith(short)) return person;
  return null;
}

// Release Please entries end with "([abc1234](.../commit/<sha>))".
const ENTRY_COMMIT = /\(\[[a-f0-9]{7,40}\]\(https:\/\/github\.com\/[^/\s)]+\/[^/\s)]+\/commit\/([a-f0-9]{7,40})\)\)/gi;

// Puts the attribution at the end of each entry. Anything already after the
// commit link (an attribution from an earlier run) is replaced.
function withAuthors(lines, people) {
  return lines.map(line => {
    if (!/^\s*[*-]\s/.test(line)) return line;
    let last = null;
    for (const match of line.matchAll(ENTRY_COMMIT)) last = match;
    if (!last) return line;
    const entry = line.slice(0, last.index + last[0].length);
    const credit = attribution(personFor(people, last[1]));
    return credit ? `${entry} ${credit}` : entry;
  });
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

// missed: [{sha, subject, number?}]
// people: Map of full lowercase commit SHA -> {author, credits}
function detailsBlock({owner, repo, missed, people = new Map()}) {
  if (!missed.length) return '';
  const lines = ['### Other Changes', ''];
  for (const commit of missed) {
    const pr = commit.number ? ` (${prLink(owner, repo, commit.number)})` : '';
    const credit = attribution(personFor(people, commit.sha));
    lines.push(`* ${escapeMarkdown(commit.subject)}${pr} (${commitLink(owner, repo, commit.sha)})${credit ? ` ${credit}` : ''}`);
  }
  return `${START}\n${lines.join('\n')}\n${END}`;
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

// Credits each entry in the version's section and replaces (or adds) the
// block at its end. Returns null when the section cannot be found.
function withDetails(text, version, block, people = new Map()) {
  const eol = (text || '').includes('\r\n') ? '\r\n' : '\n';
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n');
  const range = sectionRange(lines, version);
  if (!range) return null;
  const section = withAuthors(withoutBlock(lines.slice(range.start, range.end)), people);
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

// Finds who made each commit since the last release (the PR author and the
// PR's credits, or the commit author for direct pushes), plus the commits the
// generated notes missed.
async function collect({github, owner, repo, base, since, notes}) {
  const mainCommits = (await commitsSince(github, owner, repo, `${since}...${base}`))
    .filter(commit => (commit.parents || []).length < 2 && !RELEASE_COMMIT.test(subjectOf(commit.commit.message)));

  const prOf = new Map();
  const people = new Map();
  for (const commit of mainCommits) {
    const {data: associated} = await github.rest.repos.listPullRequestsAssociatedWithCommit(
      {owner, repo, commit_sha: commit.sha});
    const merged = associated.filter(pr => pr.merged_at && pr.base.ref === base && !isReleasePr(pr, owner, repo));
    const pr = merged.find(item => item.merge_commit_sha === commit.sha) || merged[0];
    if (pr) prOf.set(commit.sha, pr.number);
    const author = mention(pr ? pr.user : commit.author);
    const credits = pr ? creditsFrom(pr.body) : [];
    if (author || credits.length) people.set(commit.sha.toLowerCase(), {author, credits});
  }

  const covered = referencedShas(notes);
  const missed = mainCommits
    .filter(commit => !isReferenced(covered, commit.sha))
    .map(commit => {
      const number = prOf.get(commit.sha);
      return {sha: commit.sha, number, subject: stripPrSuffix(subjectOf(commit.commit.message), number)};
    });

  return {people, missed};
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

    const {people, missed} = await collect({github, owner, repo, base, since: latest.tag_name, notes});
    const block = detailsBlock({owner, repo, missed, people});

    const updated = withDetails(changelog, version, block, people);
    if (updated !== null && updated !== changelog) {
      await github.rest.repos.createOrUpdateFileContents({
        owner, repo, path: 'CHANGELOG.md', branch: release.head.ref, sha: file.sha,
        message: `chore: add authors, credits and missed changes to ${version} release notes`,
        content: Buffer.from(updated, 'utf8').toString('base64'),
      });
    }

    const body = withDetails(release.body || '', version, block, people);
    if (body === null) core.warning(`Could not find ${version} in the body of release PR #${release.number}.`);
    else if (body !== release.body) await github.rest.pulls.update({owner, repo, pull_number: release.number, body});

    core.info(`Release details for ${version}: ${people.size} credited commit(s), ${missed.length} missed commit(s).`);
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
module.exports.mention = mention;
module.exports.creditsFrom = creditsFrom;
module.exports.attribution = attribution;
module.exports.withAuthors = withAuthors;
module.exports.detailsBlock = detailsBlock;
module.exports.sectionRange = sectionRange;
module.exports.sectionLines = sectionLines;
module.exports.withDetails = withDetails;
module.exports.collect = collect;
