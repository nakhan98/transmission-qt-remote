# AGENTS.md

## Spec-driven Development

This repository uses spec-driven development to keep feature and bug work
organized. Each feature/bug lives in its own directory inside `.tmp/dev`, containing a
`spec.md` and a matching `todo.md`. Name each directory descriptively (for
example, `add_dark_theme/`).

```markdown
# Feature or Bug Title

Describe the feature or bug, including context and goals.

# Design

Outline the high-level design or fix approach. This section should double as a
lightweight ADR and evolve with the work.

# Status

Mark whether the spec is being refined, in the backlog, in progress, or completed.
```

`todo.md` should capture a checklist or bullet list of implementation steps and
be updated as tasks progress. For example:

```markdown
- [x] Confirm design constraints with logging team
- [ ] Implement client wrapper
- [ ] Add integration test for retry logic
```

**IMPORTANT: The AI agent must keep both `spec.md` and `todo.md` current while
actively working on a spec.** Update design notes with new decisions, adjust
statuses promptly, and check off completed tasks as you go.

Specs live under `.tmp/dev` in these subdirectories:

- `./.tmp/dev/wip/<feature_or_bug_dir>/` – the single spec currently in progress
- `./.tmp/dev/backlog/{feature_1_dir/, feature_2_dir/, bug_1_dir/, …}/` – queued work
- `./.tmp/dev/completed/{feature_1_dir/, bug_2_dir/, …}/` – finished specs
- `./.tmp/dev/tbd/{feature_in_refinement_1_dir/, …}/` – drafts being refined or discussed

Your human collaborator may introduce the feature or bug to you directly via
chat or they may jot them down in `./.tmp/dev/notes.txt`. If asked to process
notes.txt (please do not do so without explicit prompting as your human
collaborator may have not finished describing their thoughts there), *remove
issues from there as they are codified in specs*.

### Iterative Issue Processing
When processing complex multi-issue bugs from notes.txt:
- **One feature/bug spec per major bullet and its sub-items**: Create one
  `.tmp/dev/tbd/` directory for them.
- **Remove completed bullets**: Update notes.txt by removing major bullets once
  all sub-items are processed to feature/bug specs.

### Example: Complex Bug Breakdown
For "connection problems with 401 errors and broken UI":
```
.tmp/dev/tbd/
└── connection-bugs-fixes/           # One spec for all connection issues
   ├── spec.md: "Fix all connection-related bugs"
   └── todo.md:
       ├── [ ] Fix 401 authentication errors
       ├── [ ] Implement add server dialog
       ├── [ ] Change default timeout to 5s
       └── [ ] Fix duplicate button icons
```

Workflow guidelines:

1. Draft new specs under `tbd/`.
2. Move them to `backlog/` once the scope is clear.
3. Promote a single spec into `wip/` when active work begins.
4. Move it to `completed/` only after both documents reflect the final
   implementation and your human collaborator has verified the work.

Note: `.tmp/` is git-ignored; do not attempt to commit anything within it.

Other guidelines follow below.

## Other guidelines and information

This file provides guidance to Claude Code (claude.ai/code), Opencode, Codex
and other AI Agents when working with code in this repository.

Firstly please check README.md

### Build and Run Commands
- Setup virtual environment: `make setup_venv`
- Install dependencies: `make install`
- Run application: `make run`
- Run all tests: `make test`
- Run single test: `python -m pytest test_transmission_client.py::test_function_name -v`
- Test with coverage: `make coverage`
- Clean project: `make clean`
- Download IP2Location database: `make download_geoip`

### Code Style Guidelines
- Use type hints for all function parameters and return values
- Format docstrings using Google style with Args/Returns sections
- Import organization: standard library, third-party, local imports with blank line separations
- Use f-strings for string formatting
- Prefer descriptive variable names over abbreviations
- Error handling: use try/except blocks with specific exceptions
- Follow PEP 8 naming conventions: snake_case for functions/variables, CamelCase for classes
- Log errors using the logging module rather than print statements
- Use type annotations from typing module (List, Dict, Optional, etc.)
- For unit/integration tests, write Given/When/Then comments throughout the
  test code to improve readability and maintainability
- Regularly run ruff check and formatter as appropriate while working on python code: `make lint`.


### Git Branch Workflow
- **One feature at a time**: Work on only one feature/bug/task per branch to
  maintain clear scope and easy review
- **Branch creation**: Create feature branches from `develop` using conventional commit naming:
  - `feat/feature-name` for new features
  - `fix/bug-name` for bug fixes
  - `docs/documentation-update` for documentation changes
  - `refactor/code-improvement` for code refactoring
- **Verification required**: After implementation and testing, request human colleague verification before merging
- **Merge process**: Once verified by human colleague, merge to `develop` and delete the feature branch
- **Branch cleanup**: Remove merged branches to keep repository clean: `git branch -d feature-branch-name`

### Development Standards
- Commit messages should be concise and follow [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/).
- TODO: `.tmp/` is a local development scratch space that is git ignored.
- Regularly run unit tests to ensure functionality has not been compromised
  during feature development and bug fixing.
- For new feature try to create appropriate unit and/or integration tests.

### Other
- A copy of the the [Transmission RPC spec](https://github.com/transmission/transmission/blob/main/docs/rpc-spec.md)
  can be found at `.tmp/rpc-spec.md` (retrieved 28-11-2026).
