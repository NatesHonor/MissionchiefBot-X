'use strict';

// Posts one "CI Results" comment on a pull request covering every check run
// on its head commit (CI, PR policy, security, CodeQL, Docker, ...), not only
// the jobs of a single workflow. For each failed check it explains why it
// failed: the failing steps, the error annotations, and the error lines from
// the job log, followed by a short hint on how to fix that kind of failure.

const MARKER = '<!-- mission-checks-summary -->';
const SELF = 'summarize all PR checks';
const FAILED = ['failure', 'cancelled', 'timed_out', 'action_required', 'startup_failure', 'stale'];
const ICON = {success: '✅', failure: '❌', cancelled: '⚠️', timed_out: '⏱️', skipped: '⏭️',
  neutral: '➖', action_required: '⚠️', startup_failure: '❌', stale: '⚠️', pending: '⏳'};
const MAX_LOG_LINES = 15;
const MAX_TEXT = 1500;

// How to fix each kind of failure. Keys are matched against the check name.
const HINTS = [
  [/pr description/i, 'Fill in `## Summary` (at least 20 characters) and `## Testing` (how you checked the change) in the PR description, then save it. The check re-runs automatically.'],
  [/pr title|semantic pr title/i, 'Rename the PR so the title starts with `fix:` or `feat:`, for example `fix: stop duplicate dispatches`.'],
  [/release contract/i, 'The PR title must start with `fix:` or `feat:`, and every commit subject must be a Conventional Commit such as `fix: ...`. Reword commits with `git rebase -i` if needed.'],
  [/pr artifacts/i, 'Remove the listed files (`.env`, `config.ini`, logs, bytecode, archives or build output) from the PR and add them to `.gitignore`.'],
  [/codeql/i, 'Open the CodeQL alert from the details link, fix the flagged code path, and push again.'],
  [/dependency.?review/i, 'A dependency added or changed in this PR has a high-severity advisory. Use a patched version.'],
  [/dependency.?audit/i, 'Update the vulnerable package in `requirements.txt` to the fixed version pip-audit reports.'],
  [/freshness/i, 'Some dependencies are outdated. Update them if it is safe to do so.'],
  [/secret|gitleaks/i, 'A credential was found in the changes. Remove it, rotate it, and use an environment variable or GitHub secret instead.'],
  [/bandit/i, 'Fix the security issue Bandit reports at the file and line shown above.'],
  [/ruff|lint/i, 'Run `ruff check .` locally and fix the reported errors.'],
  [/mypy|type-check/i, 'Run the mypy command from `.github/workflows/ci.yml` locally and fix the type errors.'],
  [/compatibility/i, 'Install `requirements.txt` with Python 3.11 and run `python -c "import Main"` to reproduce the import or dependency error.'],
  [/release notifications|node/i, 'Run `node --test tests/test_release_notifications.js tests/test_release_details.js` locally to reproduce the failing test.'],
  [/docker/i, 'Run `docker build .` locally to reproduce the build error.'],
];

function hintFor(name) {
  return HINTS.find(([pattern]) => pattern.test(name))?.[1] ||
    'Open the details link to see the failing step and its log.';
}

function stateOf(check) {
  return check.status === 'completed' ? (check.conclusion || 'neutral') : 'pending';
}

// A re-run leaves the earlier check runs behind; keep only the newest of each name.
function latestChecks(checkRuns) {
  const latest = new Map();
  for (const check of checkRuns) {
    if (check.name === SELF) continue;
    const previous = latest.get(check.name);
    const time = item => new Date(item.started_at || item.completed_at || 0).getTime();
    if (!previous || time(check) > time(previous) || (time(check) === time(previous) && check.id > previous.id)) {
      latest.set(check.name, check);
    }
  }
  return [...latest.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function stripLogLine(line) {
  return line
    .replace(/^\uFEFF?\d{4}-\d{2}-\d{2}T[\d:.]+Z\s?/, '')
    .replace(/\x1b\[[0-9;]*m/g, '')
    .trimEnd();
}

// Pull the lines that explain a failure out of a raw job log.
function errorLines(log) {
  const lines = (log || '').split(/\r?\n/).map(stripLogLine);
  const wanted = /##\[error\]|\berror\b|\bfailed\b|\bfailure\b|traceback|exception|assert|not ok\b|✖|^E\s{2,}|^FAILED\b|^\s*[\w./-]+\.(py|js|cjs|ts|ya?ml):\d+/i;
  const noise = /##\[(group|endgroup|debug)\]|Node\.js \d+ (actions )?(are|is) deprecated|retry-exempt-status-codes|^\s*(if|const|let|errors\.push|core\.setFailed)\b|continue-on-error|Cleaning up orphan processes/i;
  const picked = [];
  for (const line of lines) {
    if (!line.trim() || noise.test(line) || !wanted.test(line)) continue;
    const text = line.replace(/^##\[error\]/, '').trim();
    if (text && !picked.includes(text)) picked.push(text);
  }
  return picked.slice(-MAX_LOG_LINES);
}

function clip(text, limit = MAX_TEXT) {
  const value = (text || '').trim();
  return value.length > limit ? `${value.slice(0, limit - 1)}…` : value;
}

// Never let log text close the code fence or ping someone.
function fenceSafe(text) {
  return text.replace(/```/g, "'''").replace(/@(?=[\w-])/g, '@\u200b');
}

function analysisFor(check, details) {
  const parts = [`#### ❌ \`${check.name}\` — ${stateOf(check)}`];
  if (details.steps?.length) parts.push(`**Failed step:** ${details.steps.map(step => `\`${step}\``).join(', ')}`);

  const reasons = [];
  for (const annotation of details.annotations || []) {
    const where = annotation.path && annotation.path !== '.github' ?
      `\`${annotation.path}${annotation.start_line ? `:${annotation.start_line}` : ''}\` ` : '';
    const message = clip(annotation.message, 500).split('\n').map(line => line.trim()).filter(Boolean);
    for (const line of message) if (!reasons.includes(`${where}${line}`)) reasons.push(`${where}${line}`);
  }
  const summary = [check.output?.title, check.output?.summary].filter(Boolean).map(text => clip(text, 500));

  if (reasons.length) parts.push(`**Why it failed:**\n${reasons.map(reason => `- ${reason}`).join('\n')}`);
  else if (summary.length) parts.push(`**Why it failed:** ${summary.join(' — ')}`);

  if (details.logLines?.length) {
    parts.push(`<details><summary>Error output from the log</summary>\n\n\`\`\`text\n${fenceSafe(clip(details.logLines.join('\n')))}\n\`\`\`\n</details>`);
  }
  if (!reasons.length && !summary.length && !details.logLines?.length) {
    parts.push(check.conclusion === 'cancelled' ?
      '**Why it failed:** the run was cancelled (usually superseded by a newer push, or timed out).' :
      '**Why it failed:** the check did not report a reason.');
  }
  parts.push(`**How to fix:** ${hintFor(check.name)}`);
  if (check.html_url) parts.push(`[Open the check](${check.html_url})`);
  return parts.join('\n\n');
}

function commentBody({checks, analyses, owner, repo, sha}) {
  const passed = checks.filter(check => stateOf(check) === 'success').length;
  const failed = checks.filter(check => FAILED.includes(stateOf(check)));
  const pending = checks.filter(check => stateOf(check) === 'pending');
  const skipped = checks.filter(check => ['skipped', 'neutral'].includes(stateOf(check)));

  let body = `${MARKER}\n## CI Results\n\n`;
  body += `**${passed}/${checks.length}** checks passed`;
  if (failed.length) body += ` · **${failed.length} failed**`;
  if (pending.length) body += ` · **${pending.length} still running**`;
  if (skipped.length) body += ` · ${skipped.length} skipped`;
  body += '\n\n';

  const order = check => FAILED.includes(stateOf(check)) ? 0 : stateOf(check) === 'pending' ? 1 : 2;
  for (const check of [...checks].sort((a, b) => order(a) - order(b) || a.name.localeCompare(b.name))) {
    const state = stateOf(check);
    const name = check.html_url ? `[\`${check.name}\`](${check.html_url})` : `\`${check.name}\``;
    body += `- ${ICON[state] || '❔'} ${name} (${state})\n`;
  }

  if (failed.length) {
    body += '\n### Why checks failed\n\n';
    body += failed.map(check => analyses.get(check.id) || analysisFor(check, {})).join('\n\n---\n\n');
    body += '\n';
  } else if (!pending.length && checks.length) {
    body += '\nAll checks passed.\n';
  }
  body += `\n[All checks for ${sha.slice(0, 7)}](https://github.com/${owner}/${repo}/commit/${sha}/checks)\n`;
  return body;
}

async function findPullRequest({github, owner, repo, run}) {
  const direct = (run.pull_requests || []).find(pr => pr.base?.repo?.name === repo);
  if (direct) return direct.number;
  // Pull requests from forks are not attached to workflow runs.
  const associated = await github.paginate(github.rest.repos.listPullRequestsAssociatedWithCommit,
    {owner, repo, commit_sha: run.head_sha, per_page: 100});
  const match = associated.find(pr => pr.state === 'open' && pr.head?.sha === run.head_sha);
  if (match) return match.number;
  const open = await github.paginate(github.rest.pulls.list, {owner, repo, state: 'open', per_page: 100});
  return open.find(pr => pr.head?.sha === run.head_sha)?.number || null;
}

async function failureDetails({github, owner, repo, check, core}) {
  const details = {steps: [], annotations: [], logLines: []};
  try {
    details.annotations = (await github.paginate(github.rest.checks.listAnnotations,
      {owner, repo, check_run_id: check.id, per_page: 100}))
      .filter(annotation => annotation.annotation_level === 'failure' ||
        (annotation.annotation_level === 'warning' && !/Node\.js \d+|deprecated/i.test(annotation.message || '')));
  } catch (error) {
    core.info(`No annotations for ${check.name}: ${error.message}`);
  }
  // GitHub Actions check runs share their ID with the job, which gives the
  // failed step names and the raw log.
  if (check.app?.slug !== 'github-actions') return details;
  try {
    const {data: job} = await github.rest.actions.getJobForWorkflowRun({owner, repo, job_id: check.id});
    details.steps = (job.steps || []).filter(step => FAILED.includes(step.conclusion)).map(step => step.name);
  } catch (error) {
    core.info(`No job details for ${check.name}: ${error.message}`);
  }
  try {
    const response = await github.rest.actions.downloadJobLogsForWorkflowRun({owner, repo, job_id: check.id});
    const log = typeof response.data === 'string' ? response.data :
      Buffer.isBuffer(response.data) ? response.data.toString('utf8') :
        response.data instanceof ArrayBuffer ? Buffer.from(response.data).toString('utf8') : '';
    details.logLines = errorLines(log);
  } catch (error) {
    core.info(`No log for ${check.name}: ${error.message}`);
  }
  return details;
}

async function summarize({github, context, core}) {
  const {owner, repo} = context.repo;
  const run = context.payload.workflow_run;
  if (!run) { core.info('Not a workflow_run event.'); return; }

  const number = await findPullRequest({github, owner, repo, run});
  if (!number) { core.info(`No open pull request for ${run.head_sha}.`); return; }
  const {data: pr} = await github.rest.pulls.get({owner, repo, pull_number: number});
  if (pr.head.sha !== run.head_sha) {
    core.info(`PR #${number} has moved on to ${pr.head.sha}; skipping stale results.`);
    return;
  }

  const checkRuns = await github.paginate(github.rest.checks.listForRef,
    {owner, repo, ref: run.head_sha, filter: 'latest', per_page: 100});
  const checks = latestChecks(checkRuns);

  const analyses = new Map();
  for (const check of checks.filter(item => FAILED.includes(stateOf(item)))) {
    analyses.set(check.id, analysisFor(check, await failureDetails({github, owner, repo, check, core})));
  }
  const body = commentBody({checks, analyses, owner, repo, sha: run.head_sha});

  const comments = await github.paginate(github.rest.issues.listComments,
    {owner, repo, issue_number: number, per_page: 100});
  // Also pick up the comment the old CI job used to post so it is replaced.
  const existing = comments.find(comment => comment.user?.type === 'Bot' &&
    (comment.body?.includes(MARKER) || comment.body?.startsWith('## CI Results')));
  if (existing?.body === body) return;
  if (existing) await github.rest.issues.updateComment({owner, repo, comment_id: existing.id, body});
  else await github.rest.issues.createComment({owner, repo, issue_number: number, body});
  core.info(`Updated CI results on PR #${number}: ${checks.length} checks.`);
}

module.exports = summarize;
module.exports.MARKER = MARKER;
module.exports.SELF = SELF;
module.exports.hintFor = hintFor;
module.exports.stateOf = stateOf;
module.exports.latestChecks = latestChecks;
module.exports.errorLines = errorLines;
module.exports.analysisFor = analysisFor;
module.exports.commentBody = commentBody;
module.exports.findPullRequest = findPullRequest;
