---
name: github-pr-prepare
description: Use when agent makes a GitHub PR
allowed-tools: Bash
---

- You can expect `gh` is installed and configured
- We use the git workflow: fork upstream, clone that repo (`origin`), set up `upstream` remote, create PR origin->upstream.
- When making code changes for a PR, make sure to branch off up-to-date master/main before making code changes:

```
git fetch upstream
git checkout upstream/main
```

- Before creating the PR, ensure your branch is up-to-date with upstream:
```bash
git fetch upstream
git merge upstream/main  # or `upstream/master`, depending on the repository
```

- Resolve any merge conflicts if they occur, then commit the changes.

- **CRITICAL: PR Template Usage**
  - You MUST check for a PR template in `.github/pull_request_template.md` or `.github/PULL_REQUEST_TEMPLATE/`.
  - If a template exists, you MUST read it, fill in the sections (Description, Checklist, Test Plan, etc.), and use the filled content as the body.
  - If a checklist item does not apply for the PR, mark it done.
  - DO NOT use `gh pr create` without a body if you are an AI agent, as it may require interactive input.
  - Instead, construct the body with the filled template and pass it via `--body` or `--body-file`.
  - Example:
    1. Read `.github/pull_request_template.md`
    2. Replace placeholders (TODOs) with actual content.
    3. Run:
       ```bash
       gh pr create --title "<title>" --body "<filled_template_content>"
       ```

- Avoid verbose text in PR description. Brevity is golden. Prefer bullet points. Focus on WHAT this PR achieves, what major caveats it could have. Emphasize if there is user-observable backwards incompatibility.

- **Issue linking** — depends on the tracker:
  - **GitHub issue**: put a [linking keyword](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue#linking-a-pull-request-to-an-issue-using-a-keyword) + number — `Closes #123` (or `Fixes`/`Resolves`) to close on merge, `Refs #123` to link only — on its own plain-text line; GitHub does NOT parse it inside a heading or backticks/code spans, so `` ## Fix (`Closes #123`) `` links nothing. One issue goes at the bottom of the body. For **multiple** issues, put each keyword at the bottom of the description section it relates to, not all together at the absolute bottom.
  - **Jira issue(s)**: prefix the PR title with the issue ID, joining multiple with a comma and space (`JIRA-1: <summary>` or `JIRA-1, JIRA-2: <summary>`).

- Include test results: which environment, which cloud provider, which GPUs and what the result was.

## Where this sits in the review flow

See the [review-skills map](../change-review/review-skills-map.md):
`change-review` (broad dispatch) → `/code-review` + `/security-review` (deep) →
`requesting-code-review` → `github-pr-prepare` → `receiving-code-review` → `github-pr-review`.
