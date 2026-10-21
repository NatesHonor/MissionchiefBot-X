'use strict';

const MARKER = '<!-- mission-auto-release-bot:pending-release -->';
const PR_LINK = /\[#(\d+)\]\(https:\/\/github\.com\/[^/\s)]+\/[^/\s)]+\/(?:issues|pull)\/\1\)/g;

function releaseVersion(patch) {
  // The version comes from Release Please's proposed manifest, not a PR title.
  const added = patch?.split('\n').find(line => /^\+\s*"\."\s*:\s*"\d+\.\d+\.\d+(?:-[\w.-]+)?"/.test(line));
  const match = added?.match(/"\."\s*:\s*"(\d+\.\d+\.\d+(?:-[\w.-]+)?)"/);
  return match ? `v${match[1]}` : null;
}

function message(version, release) {
  return `${MARKER}\n**Merged successfully!**\nThis pull request has been merged and is scheduled for inclusion in **${version}**.\n**Upcoming release:** [#${release.number} — Release ${version}](${release.html_url})\nYour changes will be included when the release PR is merged and the release is published.\n_— MissionAutoReleaseBot_`;
}

function releaseNotesFromDiff(diff, version) {
  const section = diff.split(/^diff --git /m)
    .find(part => part.startsWith('a/CHANGELOG.md b/CHANGELOG.md\n'));
  if (!section) return null;
  const lines = section.split('\n');
  const start = lines.findIndex(line => line.startsWith('+## ') && line.includes(`[${version.slice(1)}](`));
  if (start < 0) return null;
  let end = lines.findIndex((line, index) => index > start && /^[+ ]## /.test(line));
  if (end < 0) end = lines.length;
  return lines.slice(start, end).filter(line => line.startsWith('+') && !line.startsWith('+++'));
}

function includedNumbers(lines, owner, repo, releaseNumber) {
  const numbers = new Set();
  for (const line of lines) {
    const links = [...line.matchAll(PR_LINK)];
    if (!links.length) continue;
    const hasCommit = line.includes(`https://github.com/${owner}/${repo}/commit/`);
    for (const link of links) {
      const number = Number(link[1]);
      const target = `https://github.com/${owner}/${repo}/`;
      if (number !== releaseNumber && hasCommit && link[0].includes(target)) numbers.add(number);
    }
  }
  return numbers;
}

function confirmsCommit(lines, number, sha, owner, repo) {
  if (!sha) return false;
  return lines.some(line => {
    const prLink = `[#${number}](https://github.com/${owner}/${repo}/issues/${number})`;
    const altLink = `[#${number}](https://github.com/${owner}/${repo}/pull/${number})`;
    const commit = [...line.matchAll(new RegExp(
      `https://github\\.com/${owner}/${repo}/commit/([a-f0-9]{7,40})`, 'gi'))];
    return (line.includes(prLink) || line.includes(altLink)) &&
      commit.some(match => sha.toLowerCase().startsWith(match[1].toLowerCase()));
  });
}

async function notify({github, context, core}) {
  const {owner, repo} = context.repo;
  try {
    const base = context.payload.repository.default_branch;
    const releases = await github.paginate(github.rest.pulls.list,
      {owner, repo, state: 'open', base, per_page: 100});
    const pending = releases.filter(pr => pr.head.repo?.full_name === `${owner}/${repo}` &&
      pr.head.ref.startsWith('release-please--') &&
      pr.labels.some(label => label.name === 'autorelease: pending'));
    if (pending.length !== 1) {
      core.info(`Expected one pending Release Please PR; found ${pending.length}. Skipping.`);
      return;
    }
    const release = pending[0];
    const files = await github.paginate(github.rest.pulls.listFiles,
      {owner, repo, pull_number: release.number, per_page: 100});
    const version = releaseVersion(files.find(file => file.filename === '.release-please-manifest.json')?.patch);
    if (!version) { core.warning(`Unable to read version from release PR #${release.number} manifest diff.`); return; }
    if (!files.some(file => file.filename === 'CHANGELOG.md' && file.status === 'modified')) return;

    // The file-list patch is truncated by GitHub for large changelogs. Use the
    // full diff and fail closed if it cannot be verified.
    const response = await github.request('GET /repos/{owner}/{repo}/pulls/{pull_number}', {
      owner, repo, pull_number: release.number, headers: {accept: 'application/vnd.github.diff'}
    });
    const lines = releaseNotesFromDiff(typeof response.data === 'string' ? response.data : '', version);
    if (!lines) { core.warning(`Could not verify ${version} release notes in PR #${release.number}.`); return; }
    const numbers = includedNumbers(lines, owner, repo, release.number);
    const bot = await github.rest.apps.getAuthenticated();
    const botLogin = `${bot.data.slug}[bot]`.toLowerCase();

    for (const number of numbers) {
      try {
        const {data: pr} = await github.rest.pulls.get({owner, repo, pull_number: number});
        if (!pr.merged_at || pr.base.ref !== base ||
            (pr.head.repo?.full_name === `${owner}/${repo}` &&
             pr.head.ref.startsWith('release-please--'))) continue;
        // Squash, merge-commit and rebase PRs are accepted only when GitHub's
        // merge commit SHA is actually linked alongside this PR in release notes.
        if (!confirmsCommit(lines, number, pr.merge_commit_sha, owner, repo)) continue;
        const comments = await github.paginate(github.rest.issues.listComments,
          {owner, repo, issue_number: number, per_page: 100});
        const existing = comments.find(comment => comment.user?.type === 'Bot' &&
          comment.user.login.toLowerCase() === botLogin && comment.body?.includes(MARKER));
        const body = message(version, release);
        if (existing?.body === body) continue;
        if (existing) await github.rest.issues.updateComment({owner, repo, comment_id: existing.id, body});
        else await github.rest.issues.createComment({owner, repo, issue_number: number, body});
      } catch (error) {
        core.warning(`Could not notify PR #${number}: ${error.message}`);
      }
    }
  } catch (error) {
    core.warning(`Pending release notification skipped: ${error.message}`);
  }
}

module.exports = notify;
module.exports.releaseVersion = releaseVersion;
module.exports.releaseNotesFromDiff = releaseNotesFromDiff;
module.exports.includedNumbers = includedNumbers;
module.exports.confirmsCommit = confirmsCommit;
module.exports.message = message;
