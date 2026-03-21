# Team Conventions

This document sets out the basic working conventions for the repo.

We are using one repository, one shared `develop` branch, and feature branches for actual work. Changes should not be made directly on `develop` or `main`.

## Branching

### Main idea

- `main` is the stable branch
- `develop` is the integration branch
- all actual work happens on feature branches

### Branch rules

- always branch off the latest `develop`
- never code straight on `develop`
- never push straight to `main`
- one branch = one task, feature, bug fix, or doc change

### Branch naming

Keep branch names lowercase and obvious:

- `feat/night-bus-filter`
- `fix/mapbox-token-loading`
- `docs/setup-guide`
- `refactor/api-route-scoring`
- `test/report-validation`
- `chore/update-env-example`

Branch names should be short and descriptive.

## Pull Requests

### Where PRs go

Everything should be merged into `develop` through a pull request.

Please do not merge feature branches straight into `main`.

### When to open a PR

Open a PR when:

- the thing actually works
- you have tested the obvious bits
- the branch is focused and not full of unrelated changes

If the work is still in progress but you want feedback, open a draft PR.

### Before opening a PR

- pull the latest `develop`
- update your branch with `develop`
- sort merge conflicts on your own branch, not in the PR
- run the checks that make sense for your part
- give the PR a normal title and explain what changed

## Commit Convention

Please try to keep commit messages short and clear, please avoid vague messages like as `stuff`, `bits`, or `final version`.

Use:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for docs
- `refactor:` for code reshuffles with no feature change
- `test:` for tests
- `chore:` for setup, config, tooling, deps, housekeeping

Examples:

- `feat: add night bus filter chip group`
- `fix: stop map screen crashing without token`
- `docs: add repo conventions and architecture notes`
- `refactor: split route scoring into service layer`
- `test: cover safety report validation`
- `chore: add local redis and postgres compose setup`

## How Often To Commit

Commit regularly.

Good rule of thumb:

- commit whenever you finish a meaningful chunk
- commit before doing something risky
- commit before you stop for the day

In practice that usually means every 30-90(ish) minutes if you are actively working, or whenever a feature step is complete.

As a general guide, please try to avoid keeping large amounts of local work uncommitted for long periods.

## How Often To Push

Please try to push regularly as well to reduce the chance of losing work.

As a general heuristic:

- push at the end of each session
- push before asking for help
- push before opening a PR
- push if you have done a couple of commits and your branch is in a decent state

## Keeping Branches Healthy

- pull `develop` before creating a new branch
- if your branch lives longer than a day or two, update it from `develop`
- keep PRs reasonably small
- do not mix frontend, backend, infra and docs changes in one branch unless they are genuinely tied together

## What Not To Commit

Please don't commit:

- `.env` files
- secrets, API keys, tokens, passwords
- random local cache files
- broken half-generated code you have not checked

## Team Workflow

The normal flow to try to keep to:

1. pull latest `develop`
2. create a branch
3. do the work
4. commit properly as you go
5. push the branch
6. open a PR into `develop`
7. get it reviewed
8. merge it