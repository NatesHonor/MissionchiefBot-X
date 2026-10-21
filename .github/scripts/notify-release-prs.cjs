'use strict';

const MARKER = '<!-- mission-auto-release-bot:pending-release -->';
const CREDITS_MARKER = '<!-- mission-auto-release-bot:credits -->';
const PR_LINK = /\[#(\d+)\]\(https:\/\/github\.com\/[^/\s)]+\/[^/\s)]+\/(?:issues|pull)\/\1\)/g;
const PENDING_HEADER = '**Merged successfully!**';

function releaseVersion(patch) {
  // The version comes from Release Please's proposed manifest, not a PR title.
  const added = patch?.split('\n').find(line => /^\+\s*"\."\s*:\s*"\d+\.\d+\.\d+(?:-[\w.-]+)?"/.test(line));
  const match = added?.match(/"\."\s*:\s*"(\d+\.\d+\.\d+(?:-[\w.-]+)?)"/);
  return match ? `v${match[1]}` : null;
}

function message(version, release) {
  return `${MARKER}\n${PENDING_HEADER}\nThis pull request has been merged and is scheduled for inclusion in **${version}**.\n**Upcoming release:** [#${release.number} — Release ${version}](${release.html_url})\nYour changes will be included when the release PR is merged and the release is published.\n_— MissionAutoReleaseBot_`;
}

function releasedMessage(version, release) {
  return `${MARKER}\n**Released!**\nThis pull request was included in **${version}**.\n**Release:** [${version}](${release.html_url})\n_— MissionAutoReleaseBot_`;
}

// credits: Map of login -> sorted PR numbers. Returns markdown or '' if empty.
function creditsSection(credits) {
  const entries = [...credits.entries()].sort(([a], [b]) => a.localeCompare(b));
  if (!entries.length) return '';
  const lines = entries.map(([login, numbers]) =>
    `* Thanks to @${login} for ${numbers.map(number => `#${number}`).join(', ')}`);
  return `${CREDITS_MARKER}\n### Credits\n\n${lines.join('\n')}`;
}

function creditsComment(version, credits) {
  const section = creditsSection(credits);
  if (!section) return '';
  return `${section}\n\nThank you to everyone who contributed to **${version}**!\n_— MissionAutoReleaseBot_`;
}

// Replace (or append) the credits block in a release body. Everything from the
// marker onward belongs to the bot, so release notes above it are untouched.
function withCredits(body, credits) {
  const notes = (body || '').split(CREDITS_MARKER)[0].trimEnd();
  const section = creditsSection(credits);
  return section ? `${notes}\n\n${section}\n` : `${notes}\n`;
}

function isBot(user) {
  return !user || user.type === 'Bot' || /\[bot\]$/i.test(user.login || '');
}

function addCredit(credits, pr) {
  if (isBot(pr.user)) return;
  const numbers = credits.get(pr.user.login) || [];
  if (!numbers.includes(pr.number)) numbers.push(pr.number);
  numbers.sort((a, b) => a - b);
  credits.set(pr.user.login, numbers);
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

// Published release bodies use the same entry format as CHANGELOG.md, without
// diff markers. Prefix them so the same matching functions apply. The bot's own
// credits block is ignored so it never counts as release notes.
function releaseBodyLines(body) {
  return (body || '').split(CREDITS_MARKER)[0].split(/\r?\n/).map(line => `+${line}`);
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

async function findBotComment({github, owner, repo, number, botLogin, marker = MARKER}) {
  const comments = await github.paginate(github.rest.issues.listComments,
    {owner, repo, issue_number: number, per_page: 100});
  return comments.find(comment => comment.user?.type === 'Bot' &&
    comment.user.login.toLowerCase() === botLogin && comment.body?.includes(marker));
}

async function upsertComment({github, owner, repo, number, existing, body}) {
  if (existing?.body === body) return;
  if (existing) await github.rest.issues.updateComment({owner, repo, comment_id: existing.id, body});
  else await github.rest.issues.createComment({owner, repo, issue_number: number, body});
}

// Returns the merged PR when it is genuinely part of these release notes, else null.
async function qualifyingPr({github, owner, repo, number, base, lines}) {
  const {data: pr} = await github.rest.pulls.get({owner, repo, pull_number: number});
  if (!pr.merged_at || pr.base.ref !== base ||
      (pr.head.repo?.full_name === `${owner}/${repo}` && pr.head.ref.startsWith('release-please--'))) {
    return null;
  }
  // Squash, merge-commit and rebase PRs only qualify when GitHub's merge commit
  // SHA is linked alongside this PR in the release notes.
  return confirmsCommit(lines, number, pr.merge_commit_sha, owner, repo) ? pr : null;
}

// Comment on merged PRs listed in the pending Release Please PR, and keep a
// credits comment on the release PR itself.
async function notifyPending({github, context, core, base, botLogin}) {
  const {owner, repo} = context.repo;
  const open = await github.paginate(github.rest.pulls.list,
    {owner, repo, state: 'open', base, per_page: 100});
  const pending = open.filter(pr => pr.head.repo?.full_name === `${owner}/${repo}` &&
    pr.head.ref.startsWith('release-please--') &&
    pr.labels.some(label => label.name === 'autorelease: pending'));
  if (pending.length !== 1) {
    core.info(`Expected one pending Release Please PR; found ${pending.length}. Skipping pending notices.`);
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

  const credits = new Map();
  for (const number of includedNumbers(lines, owner, repo, release.number)) {
    try {
      const pr = await qualifyingPr({github, owner, repo, number, base, lines});
      if (!pr) continue;
      addCredit(credits, pr);
      const existing = await findBotComment({github, owner, repo, number, botLogin});
      await upsertComment({github, owner, repo, number, existing, body: message(version, release)});
    } catch (error) {
      core.warning(`Could not notify PR #${number}: ${error.message}`);
    }
  }

  // The release PR body is regenerated by Release Please and parsed when the
  // release is created, so credits live in a bot comment instead of the body.
  try {
    const body = creditsComment(version, credits);
    if (body) {
      const existing = await findBotComment({github, owner, repo, number: release.number,
        botLogin, marker: CREDITS_MARKER});
      await upsertComment({github, owner, repo, number: release.number, existing, body});
    }
  } catch (error) {
    core.warning(`Could not update credits on release PR #${release.number}: ${error.message}`);
  }
}

// Comment on merged PRs listed in already-published releases and add a credits
// section to each release. Turns an existing "scheduled" notice into a
// "released" one, and fills in PRs that were never notified. Each PR keeps the
// newest release that lists it.
async function notifyReleased({github, context, core, base, botLogin}) {
  const {owner, repo} = context.repo;
  const releases = (await github.paginate(github.rest.repos.listReleases, {owner, repo, per_page: 100}))
    .filter(item => !item.draft && !item.prerelease)
    .sort((a, b) => new Date(b.published_at) - new Date(a.published_at));
  const done = new Set();
  for (const release of releases) {
    const lines = releaseBodyLines(release.body);
    const credits = new Map();
    for (const number of includedNumbers(lines, owner, repo, -1)) {
      try {
        const pr = await qualifyingPr({github, owner, repo, number, base, lines});
        if (!pr) continue;
        addCredit(credits, pr);
        if (done.has(number)) continue;
        done.add(number);
        const existing = await findBotComment({github, owner, repo, number, botLogin});
        await upsertComment({github, owner, repo, number, existing,
          body: releasedMessage(release.tag_name, release)});
      } catch (error) {
        core.warning(`Could not backfill PR #${number}: ${error.message}`);
      }
    }
    try {
      if (!credits.size) continue;
      const body = withCredits(release.body, credits);
      if (body !== release.body) await github.rest.repos.updateRelease({owner, repo, release_id: release.id, body});
    } catch (error) {
      core.warning(`Could not add credits to ${release.tag_name}: ${error.message}`);
    }
  }
}

async function notify({github, context, core, appSlug, backfill = false}) {
  try {
    if (!appSlug) { core.warning('App slug missing; cannot identify bot comments. Skipping.'); return; }
    const base = context.payload.repository.default_branch;
    const botLogin = `${appSlug}[bot]`.toLowerCase();
    // Published releases first, so a later pending notice is never overwritten
    // by an older release in the same run.
    if (backfill) await notifyReleased({github, context, core, base, botLogin});
    await notifyPending({github, context, core, base, botLogin});
  } catch (error) {
    core.warning(`Release notification skipped: ${error.message}`);
  }
}

module.exports = notify;
module.exports.releaseVersion = releaseVersion;
module.exports.releaseNotesFromDiff = releaseNotesFromDiff;
module.exports.releaseBodyLines = releaseBodyLines;
module.exports.includedNumbers = includedNumbers;
module.exports.confirmsCommit = confirmsCommit;
module.exports.message = message;
module.exports.releasedMessage = releasedMessage;
module.exports.creditsSection = creditsSection;
module.exports.creditsComment = creditsComment;
module.exports.withCredits = withCredits;
module.exports.addCredit = addCredit;
