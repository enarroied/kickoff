# Kickoff CLI — Project Specification

## Table of Contents

- [Kickoff CLI — Project Specification](#kickoff-cli--project-specification)
  - [Table of Contents](#table-of-contents)
  - [1. Purpose](#1-purpose)
  - [2. Locked Decisions](#2-locked-decisions)
  - [3. CLI Name](#3-cli-name)
  - [4. Package Architecture](#4-package-architecture)
    - [4.1 Repository layout](#41-repository-layout)
    - [4.2 Design principle](#42-design-principle)
  - [5. Global Configuration](#5-global-configuration)
    - [5.1 Location](#51-location)
    - [5.2 Schema](#52-schema)
    - [5.3 Management commands](#53-management-commands)
  - [6. Command Tree](#6-command-tree)
  - [7. Templates](#7-templates)
    - [7.1 Template data model](#71-template-data-model)
    - [7.2 Template `default`](#72-template-default)
    - [7.3 Template `django`](#73-template-django)
    - [7.4 Template `jupyter`](#74-template-jupyter)
  - [8. Execution Flow of `kickoff new`](#8-execution-flow-of-kickoff-new)
  - [9. OpenCode Artifacts](#9-opencode-artifacts)
    - [9.1 `AGENTS.md` (root)](#91-agentsmd-root)
    - [9.2 Skills](#92-skills)
  - [10. Docker Details](#10-docker-details)
    - [10.1 `docker-compose.yml`](#101-docker-composeyml)
    - [10.2 `compose.override.yml`](#102-composeoverrideyml)
    - [10.3 `.env.example`](#103-envexample)
    - [10.4 Port strategy](#104-port-strategy)
  - [11. CI Details](#11-ci-details)
  - [12. Error Handling](#12-error-handling)
  - [13. Testing](#13-testing)
  - [14. Roadmap](#14-roadmap)
    - [v0.1 — MVP](#v01--mvp)
    - [v0.2](#v02)
    - [v0.3](#v03)
    - [v0.4+](#v04)
  - [15. Deferred / Not in Scope](#15-deferred--not-in-scope)
  - [16. Open Questions](#16-open-questions)

---

## 1. Purpose

Build a globally-installed Python CLI tool named **`kickoff`** that scaffolds new development projects in a single command. The tool standardizes:

- Project folder structure
- Python environment and dependency management (via `uv`)
- Code quality tooling (Ruff, Vulture, Pytest, pre-commit, pip-audit)
- Git initialization with a `master` default branch
- GitHub repository creation and initial push
- GitHub Actions CI workflows
- AI-agent artifacts (OpenCode: `AGENTS.md` + skills)
- Optional Docker setup with PostgreSQL and auxiliary services

> **Guiding principle:** all configuration complexity is encapsulated once inside the generator, so every new project is ready to code in one command.

---

## 2. Locked Decisions

| Topic | Decision |
|---|---|
| Language | Python |
| CLI framework | Typer |
| Env/deps manager | uv |
| Global install | `uv tool install` |
| Templates | `default`, `django`, `jupyter` (extensible) |
| Default Git branch | `master` |
| GitHub repo creation | Yes, via `gh` CLI |
| Repo visibility | Public by default, `--private` available |
| CI | GitHub Actions in the first commit |
| OpenCode artifacts | `AGENTS.md` + `.opencode/skills/` in **every** template |
| Docker | Optional via `--docker`, orthogonal to template |
| Database | Optional via `--db {none,postgres,postgis}` |
| Auxiliary services | Independent flags (`--with-pgadmin`, later `--with-redis`, `--with-minio`) |
| Compose profiles | External services unprofiled; app under `full` profile |
| DB values | Derived from project name, `--db-password` for override |
| DB ports | **Not exposed** on host by default; `--expose-db` to expose |
| App port | Exposed on host by default (8000); `--app-port` to change |
| Django server | `uvicorn` (ASGI) by default |
| Jupyter dataframe | Polars |
| Admin DB tool | pgAdmin (Adminer removed) |
| License | MIT |
| Vulture | `min_confidence = 80` |
| **Language of all artifacts** | **English only** (CLI messages, help, generated files, comments, commit messages) |
| Traefik | Documented strategy; `--traefik` flag deferred to post-MVP |

---

## 3. CLI Name

**`kickoff`** — confirmed.

Entry point in `pyproject.toml`:

```toml
[project.scripts]
kickoff = "kickoff.cli:app"
```

---

## 4. Package Architecture

### 4.1 Repository layout

```text
kickoff/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   └── kickoff/
│       ├── __init__.py
│       ├── cli.py                    # Typer entry point
│       ├── config.py                 # global config loader
│       ├── models.py                 # dataclasses (ProjectSpec, TemplateSpec, DockerConfig)
│       ├── exceptions.py
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── new.py                # `kickoff new`
│       │   └── config_cmd.py         # `kickoff config`
│       ├── generators/
│       │   ├── __init__.py
│       │   ├── structure.py          # directory tree creation
│       │   ├── files.py              # base file writing
│       │   ├── pyproject.py          # pyproject.toml enrichment
│       │   ├── git.py                # git init, add, commit
│       │   ├── github.py             # gh repo create + push
│       │   ├── docker.py             # Dockerfile, compose, .env, .dockerignore
│       │   ├── opencode.py           # AGENTS.md + skills
│       │   └── ci.py                 # GitHub Actions workflows
│       ├── templates/
│       │   ├── __init__.py
│       │   ├── base.py               # TemplateSpec dataclass
│       │   ├── default_template.py
│       │   ├── django_template.py
│       │   └── jupyter_template.py
│       ├── assets/                   # static reusable content
│       │   ├── gitignore/
│       │   ├── readme/
│       │   ├── ci/
│       │   ├── docker/
│       │   └── opencode/
│       └── utils/
│           ├── __init__.py
│           ├── shell.py              # safe subprocess wrappers
│           ├── prompts.py            # Rich interactive prompts
│           └── logging.py
└── tests/
    ├── conftest.py
    ├── test_cli.py
    ├── test_generators/
    └── fixtures/
```

### 4.2 Design principle

Templates are plain Python dataclasses (`TemplateSpec`), **not** Jinja2 templates. File content is generated by Python functions that compose reusable helpers. This keeps everything debuggable in pure Python with no template-syntax pollution.

---

## 5. Global Configuration

### 5.1 Location

`~/.config/kickoff/config.toml` (respects the XDG Base Directory specification).

### 5.2 Schema

```toml
[user]
name = "First Last"
email = "email@example.com"
github_username = "username"
author_name_from_git = true       # if true, read from `git config --global`

[defaults]
template = "default"
branch = "master"
python_version = "3.12"
license = "MIT"
repo_visibility = "public"
server = "uvicorn"

[docker]
default_db = "none"
default_app_port = 8000
default_db_port = 5432

[github]
create_repo = true
push_initial = true
```

### 5.3 Management commands

```text
kickoff config init          # interactive creation
kickoff config show          # display current config
kickoff config edit          # open in $EDITOR
kickoff config set <key> <value>
```

---

## 6. Command Tree

```text
kickoff
├── new <name>               # create a new project
│   ├── --template, -t       default | django | jupyter
│   ├── --path, -p           parent directory (default: cwd)
│   ├── --python             3.11 | 3.12 | 3.13
│   ├── --license            MIT | Apache-2.0 | GPL-3.0 | none
│   ├── --private / --public
│   ├── --no-github          skip GitHub repo creation
│   ├── --no-git             skip git init
│   ├── --no-push            create repo but don't push
│   ├── --docker             enable Docker artifacts
│   ├── --db                 none | postgres | postgis
│   ├── --db-password        override derived password
│   ├── --expose-db          expose DB port on host
│   ├── --db-port            host port for DB (only with --expose-db)
│   ├── --app-port           host port for app (default: 8000)
│   ├── --with-pgadmin       add pgAdmin service
│   ├── --server             uvicorn | gunicorn (django)
│   ├── --no-ci              skip GitHub Actions
│   ├── --no-opencode        skip OpenCode files
│   ├── --dry-run            show plan without executing
│   ├── --force              overwrite existing folder
│   └── --yes, -y            non-interactive
├── config                   # global config management
│   ├── init
│   ├── show
│   ├── edit
│   └── set
├── templates                # list available templates
└── --version
```

---

## 7. Templates

### 7.1 Template data model

```python
@dataclass
class TemplateSpec:
    name: str
    description: str
    directories: list[str]
    base_files: dict[Path, str]
    dependencies: list[str]
    dev_dependencies: list[str]
    ruff_config: dict
    vulture_config: dict
    ci_jobs: list[str]
    opencode_skills: list[str]
    docker_config: DockerConfig
```

### 7.2 Template `default`

**Target:** generic Python projects (data engineering, scripts, libraries).

**Structure:**

```text
<project>/
├── src/<package>/__init__.py
├── tests/__init__.py
├── docs/
├── scripts/
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── notebooks/
├── pyproject.toml
├── README.md
├── .gitignore
├── .pre-commit-config.yaml
├── AGENTS.md
└── .opencode/
    └── skills/
        ├── project-structure/SKILL.md
        ├── code-quality/SKILL.md
        ├── testing/SKILL.md
        └── git-workflow/SKILL.md
```

**Configuration:**

| Item | Value |
|---|---|
| Prod deps | `typer` |
| Dev deps | `ruff`, `vulture`, `pytest`, `pytest-cov`, `pre-commit`, `pip-audit` |
| Ruff rules | `E`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`, `VUT` |
| Vulture | `min_confidence = 80`, `paths = ["src"]`, `sort_by_size = true` |
| CI | lint (ruff), format-check, test (matrix 3.12/3.13), vulture, pip-audit |

### 7.3 Template `django`

**Target:** Django web applications.

**Structure:** default structure plus `manage.py`, a Django project created via `django-admin startproject`, a `core` app, `templates/`, `static/`, and `media/`.

| Item | Value |
|---|---|
| Prod deps | `django`, `typer`, `uvicorn`, `psycopg[binary]` (if Postgres) |
| Dev deps | default + `pytest-django`, `django-stubs`, `django-stubs-ext`, `factory-boy` |
| Ruff | default + `DJ` rules, `known-first-party = ["<project>", "core"]` |
| CI | lint, format, test with Postgres service, `manage.py check --deploy`, `manage.py migrate --check` |
| Docker | multi-stage Dockerfile with uvicorn, entrypoint running `migrate` + `collectstatic`, healthcheck |

### 7.4 Template `jupyter`

**Target:** exploration, data science, rapid prototyping.

**Structure:**

```text
<project>/
├── notebooks/
├── src/<package>/
├── data/
├── outputs/
├── pyproject.toml
├── README.md
├── .gitignore
├── AGENTS.md
└── .opencode/skills/...
```

| Item | Value |
|---|---|
| Prod deps | `jupyterlab`, `ipykernel`, `polars`, `typer` |
| Dev deps | `ruff`, `vulture`, `pytest`, `nbval`, `pre-commit`, `pip-audit` |
| Ruff | default + `extend-per-file-ignores = { "*.ipynb" = ["E402", "F401", "F403", "F405"] }` |
| CI | lint (excluding notebooks), test with `nbval` on a smoke notebook |

---

## 8. Execution Flow of `kickoff new`

1. **Parse arguments** (Typer).
2. **Load global config** and merge with CLI flags (flags > config > defaults).
3. **Validate:** project name, target folder (nonexistent or `--force`), template known, flag consistency (`--db postgres` without `--docker` → warning or auto-enable).
4. **Interactive summary** (unless `--yes`): show what will be created and ask for confirmation.
5. **Create** project folder and directory tree.
6. **Run `uv init`** in the folder (`--app` or `--lib` mode per template).
7. **Write base files:** README, `.gitignore`, LICENSE, `.pre-commit-config.yaml`.
8. **Enrich `pyproject.toml`:** `[tool.ruff]`, `[tool.vulture]`, `[tool.pytest.ini_options]`, project metadata.
9. **`uv add`** prod and dev dependencies.
10. **Generate OpenCode artifacts:** `AGENTS.md` + template-adapted skills.
11. **Generate GitHub Actions** workflow(s).
12. **If `--docker`:** generate Dockerfile, compose files, `.env`, `.dockerignore`.
13. **Git init:** `git init -b master`, `git add .`, first commit.
14. **Install pre-commit hooks:** `pre-commit install`.
15. **GitHub creation** (if enabled): `gh repo create <name> --source=. --push --public/--private`.
16. **Final summary:** how to start, next steps.

**On failure:** clear message; partial state is preserved (no automatic rollback). An optional `.kickoff-state.json` allows resuming.

---

## 9. OpenCode Artifacts

### 9.1 `AGENTS.md` (root)

Sections:

- **Project context** — name, template, description
- **Stack** — Python version, tooling
- **Repo structure** — commented tree
- **Commands** — build, lint, test, run (template-specific)
- **Conventions** — `master` branch, Conventional Commits, Python naming
- **Agent notes** — always use `uv run`, respect Ruff, check with Vulture

### 9.2 Skills

Each skill lives in `.opencode/skills/<name>/SKILL.md` with YAML frontmatter.

| Skill | Scope |
|---|---|
| `project-structure` | Where to put what, commented tree |
| `code-quality` | Ruff + Vulture commands, how to fix |
| `testing` | Pytest, conventions, fixtures (adapted per template) |
| `git-workflow` | `master` branch, Conventional Commits, PR flow |
| `docker-workflow` | (if `--docker`) Compose commands, profiles |

**Language:** all skills and `AGENTS.md` are written in English, regardless of the template.

---

## 10. Docker Details

### 10.1 `docker-compose.yml`

```yaml
services:
  db:
    image: postgres:16-alpine        # or postgis/postgis:16-3.4
    env_file: .env
    volumes: [pgdata:/var/lib/postgresql/data]
    expose:
      - "5432"                       # internal only by default
    healthcheck: ...

  pgadmin:                           # if --with-pgadmin
    image: dpage/pgadmin4:latest
    env_file: .env
    # no host ports by default

  app:                               # under profile "full"
    profiles: [full]
    build: .
    env_file: .env
    depends_on: { db: { condition: service_healthy } }
    ports:
      - "${APP_PORT:-8000}:8000"

volumes:
  pgdata:
```

### 10.2 `compose.override.yml`

- Mounts code as a volume in `app`
- Enables reload
- Exposes debug port

### 10.3 `.env.example`

Values derived from the project name (`POSTGRES_USER=<project>`, etc.). Overridable via `--db-password`.

### 10.4 Port strategy

- **DB, pgAdmin:** no host ports by default. Only reachable from other containers on the project's internal network.
- **App:** host port exposed by default (8000), configurable via `--app-port`.
- **`--expose-db`:** exposes the DB port on the host (useful for DBeaver or external tools).

This ensures no collisions between multiple projects on the same machine, and nothing is exposed to the local network unless explicitly requested.

---

## 11. CI Details

Workflows are generated in `.github/workflows/`:

- **`ci.yml`** — lint + format + test + vulture + pip-audit
- **Django:** adds a Postgres service to the test job
- **Jupyter:** runs `nbval` on a smoke notebook

---

## 12. Error Handling

| Case | Behavior |
|---|---|
| Target folder exists | Abort with message, unless `--force` |
| `gh` not installed | Warning, skip GitHub, continue |
| `gh` not authenticated | Warning, skip GitHub, continue |
| `uv` not installed | Fatal error (hard dependency) |
| Local Postgres on port | Warning, suggest alternative `--db-port` |
| Invalid project name | Error with expected regex |
| Unknown template | Error + list of available templates |

---

## 13. Testing

- **Unit:** each generator tested in isolation with `tmp_path`.
- **Integration:** end-to-end `kickoff new` in `--no-github --no-git` mode on a temp folder, verifying tree and content.
- **Project CI:** the `kickoff` project itself uses the same tools it generates (dogfooding).

---

## 14. Roadmap

### v0.1 — MVP

- Template `default` only
- Git init + first commit
- Ruff, Vulture, Pytest, pre-commit, pip-audit, Typer
- Basic `AGENTS.md`

### v0.2

- Template `django` (uvicorn, ASGI)
- GitHub integration (`gh repo create`)
- GitHub Actions CI

### v0.3

- Template `jupyter` (Polars)
- Docker + Postgres/PostGIS
- Full OpenCode skills

### v0.4+

- Auxiliary services: `--with-pgadmin`, `--with-redis`, `--with-minio`, `--with-mail`
- Global config (`kickoff config`)
- Extra commands (`kickoff add <feature>`)
- User-defined custom templates
- Optional `--traefik` flag for reverse-proxy-based home lab setups

---

## 15. Deferred / Not in Scope

- **Traefik integration:** documented as a future strategy; `--traefik` flag postponed.
- **Adminer:** removed; pgAdmin is the only DB UI option.
- **Redis, MinIO, Mailpit:** deferred to v0.4.
- **Multi-project orchestration:** out of scope; each project is self-contained.

---

## 16. Open Questions

None. All previously open points have been resolved:

| Point | Resolution |
|---|---|
| CLI name | `kickoff` |
| Django server | `uvicorn` (ASGI) |
| Jupyter dataframe | Polars |
| Admin DB tool | pgAdmin |
| Redis / MinIO | v0.4 |
| License | MIT |
| Vulture confidence | 80 |
| Language of artifacts | English |
| Language of CLI | English |
| Postgres port | 5432 (internal only by default) |
| DB prompt behavior | No prompt; values derived from project name |
| pgAdmin vs Adminer | pgAdmin only |
