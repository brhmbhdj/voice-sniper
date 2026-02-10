<!-- Copilot instructions for AI coding agents -->

# Copilot instructions (repository-specific)

This repository currently contains no source files at the workspace root. These instructions tell an AI coding agent how to discover the project's structure, what to check for, and how to proceed when files are missing.

1. Quick repo check
   - Confirm the repository is empty by listing the top-level files.
   - If empty, immediately ask the human maintainer which language/framework and intended entry point (e.g. `pyproject.toml`, `package.json`, `README.md`) to scaffold or inspect.

2. Discovery checklist (run in repo root)
   - Look for common language markers and infer architecture:

```bash
ls -a
git status --porcelain
rg --hidden --glob '!node_modules' 'pyproject.toml|requirements.txt|package.json|Dockerfile|README.md|main.py|app.py|manage.py' || true
``` 

   - If you find `pyproject.toml` / `requirements.txt` → treat as Python project. Look for `src/`, `app/`, `manage.py` (Django) or `main.py`/`app.py` (Flask/FastAPI).
   - If you find `package.json` → treat as JS/TS project. Look for `src/`, `server/`, `frontend/`, `vite.config`, `next.config`.
   - If you find `Dockerfile` or `k8s/` → check for containerized workflows and build scripts.

3. Architecture analysis steps
   - When files exist, identify service boundaries by scanning for top-level directories (examples: `backend/`, `frontend/`, `services/`, `worker/`).
   - Trace data flows by locating API entrypoints (HTTP handlers, CLI commands, message queue producers/consumers). Use these heuristics:
     - Search for route decorators (e.g. `@app.route`, `@router.get`) or framework files (`routes/`, `controllers/`).
     - Search for `Celery`, `rabbitmq`, `kafka`, or `redis` to find async/work queue integrations.
     - Search for `SQLAlchemy`, `alembic`, `migrations`, `prisma`, `typeorm` for DB patterns.

4. Developer workflow & commands
   - If Python: prefer creating a venv and installing dependencies; run tests with `pytest` if present.
   - If Node: run `npm ci` or `pnpm install` and `npm test`.
   - If Dockerfile present: build and run a container for integration checks.

5. Agent behaviour rules (must follow)
   - Do not modify files until you can point to at least one existing target file and explain the change in one line.
   - When the repo is empty, ask the maintainer whether to scaffold a starter layout, and which framework to use.
   - Prefer small, incremental changes with tests or a smoke-run when possible.

6. What to ask the user (examples)
   - Which language/framework should I assume for scaffolding?
   - Do you want a minimal runnable scaffold (yes/no)? If yes, should it include Docker and tests?

7. Where to look next (files that reveal architecture quickly)
   - `README.md`, `pyproject.toml`, `package.json`, `Dockerfile`, `k8s/`, `src/`, `backend/`, `frontend/`, `migrations/`.

If this file should be merged with an existing `.github/copilot-instructions.md`, open the existing file and preserve any project-specific examples before applying changes.

---
Please confirm the intended language and whether you want me to scaffold a minimal project layout now.
