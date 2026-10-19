# kickoff

Scaffold a new Python project in a single command: `src/` layout, `uv` environment, Ruff, Vulture,
Pytest, pre-commit, pip-audit, GitHub Actions workflows (CI + weekly security audit), `.env` files,
a `LICENSE`, README badges, OpenCode agent files (`AGENTS.md` + skills) and, optionally, a GitHub
repository, all configured the same way every time.

> **Status:** v0.4.1. Templates: `default`, `django`, `jupyter` and your own
> ([custom templates](#custom-templates)). Optional features: Prefect, dbt, Docker with PostgreSQL /
> PostGIS, pgAdmin, Redis, an S3 store, Mailpit and Traefik routing. Add features later with
> [`kickoff add`](#kickoff-add).

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) (hard requirement; a recent release, since `uv init --bare` and
  `--no-workspace` are used)
- `git` (optional; skipped with a warning if missing)
- [`gh`](https://cli.github.com/), authenticated with `gh auth login` (optional; GitHub creation is
  skipped with a warning if it is missing or not logged in)

## Install

```bash
uv tool install --editable .
```

## Quick start

```bash
kickoff new my-project                       # default template; shows a summary and asks to confirm
kickoff new my-site --template django        # Django (ASGI) project
kickoff new my-project --private --yes       # private GitHub repo, no confirmation
kickoff new my-project --no-github --no-ci   # local only
kickoff new my-project --python 3.13 --license Apache-2.0
kickoff new my-project --with-prefect --with-dbt --dbt-adapter postgres
kickoff new lab --template jupyter           # JupyterLab + Polars, notebook smoke test in CI
kickoff new my-site --template django --db postgres --with-pgadmin   # + Docker, PostgreSQL, pgAdmin
kickoff new my-site --template django --db postgres --with-redis --with-mail --traefik
kickoff add prefect                          # extend an existing project later (run inside it)
kickoff new my-project --dry-run             # print the plan, change nothing
```

> **Heads up:** unless you pass `--no-github` (or `--no-git`, or set `github.create_repo = false` in
> the config), `kickoff new` creates a **public** GitHub repository and pushes to it. The summary
> screen states this before anything happens; use `--private` or `defaults.repo_visibility =
> "private"` to change the default.

## Command reference

```text
kickoff [--version] [--help]
├── new <name> [OPTIONS]        create a new project
├── add <feature> [OPTIONS]     add a feature to a project created by kickoff
├── templates                   list available templates (built-in and custom)
└── config
    ├── path                    print where the configuration file lives
    ├── show                    print the effective configuration
    ├── init                    write ~/.config/kickoff/config.toml with the built-in defaults
    ├── set <key> <value>       change one value
    └── edit                    open the file in $EDITOR
```

### Global options

| Option | Description |
|---|---|
| `--version` | Print the installed kickoff version and exit. |
| `--help` | Show help (works on every command). |

### `kickoff new <NAME>`

**Argument**

| Argument | Description |
|---|---|
| `NAME` | Project name. Must match `^[A-Za-z][A-Za-z0-9_-]*$`. The Python package name is the name lower-cased with `-` replaced by `_` (`my-project` → `my_project`). |

**Options**

Defaults marked *config* come from the [global configuration](#configuration), which in turn falls
back to the built-in values in `src/kickoff/defaults.py`.

| Option | Description | Default | Status |
|---|---|---|---|
| `--template`, `-t` | `default`, `django` or `jupyter`. | *config* (`default`) | Available |
| `--path`, `-p` | Parent directory. The project is created in `<path>/<name>`. | current directory | Available |
| `--python` | Python version: `3.11`, `3.12` or `3.13`. Sets `requires-python`, `.python-version`, Ruff's `target-version`, the AGENTS.md stack line and the start of the CI matrix. | *config* (`3.12`) | Available |
| `--license` | `MIT`, `Apache-2.0`, `GPL-3.0` or `none`. Writes `LICENSE` and `project.license` in `pyproject.toml`. | *config* (`MIT`) | Available |
| `--private` / `--public` | Visibility of the GitHub repository. | *config* (`public`) | Available |
| `--no-github` | Do not create a GitHub repository. | off | Available |
| `--no-git` | Skip `git init`, the first commit, the pre-commit hook installation and (implicitly) GitHub. | off | Available |
| `--no-push` | Create the GitHub repo and the `origin` remote, but do not push. | off | Available |
| `--no-ci` | Skip both GitHub Actions workflows (`ci.yml` and `security.yml`) and the CI/Security badges. | off | Available |
| `--no-opencode` | Skip `AGENTS.md` and `.opencode/skills/`. | off | Available |
| `--with-prefect` | Add Prefect: example flow, `prefect.yaml`, tests. See [Features](#features). | off | Available |
| `--with-dbt` | Add a dbt project in `dbt/` with the chosen adapter. See [Features](#features). | off | Available |
| `--dbt-adapter` | `postgres`, `duckdb` or `sqlite`. Requires `--with-dbt` (an error otherwise). | *config* (`duckdb`) | Available |
| `--server` | `uvicorn` or `gunicorn`. Django template only (ignored, with a warning, elsewhere). | *config* (`uvicorn`) | Available |
| `--docker` | Generate `Dockerfile`, `docker-compose.yml`, `compose.override.yml`, `.dockerignore`. See [Docker and databases](#docker-and-databases). | off | Available |
| `--db` | `none`, `postgres` or `postgis`. Anything but `none` enables `--docker` (with a warning if you did not pass it). | *config* (`none`) | Available |
| `--db-password` | Database password. Needs `--db`. | generated, random | Available |
| `--expose-db` | Publish the database port on the host, bound to `127.0.0.1`. Needs `--db`. | off | Available |
| `--db-port` | Host port of the database. Only valid together with `--expose-db`; kickoff warns if the port is already in use. | *config* (`5432`) | Available |
| `--app-port` | Host port of the app container. | *config* (`8000`) | Available |
| `--with-pgadmin` | Add a pgAdmin service. Needs `--db`. | off | Available |
| `--with-redis` | Add a Redis service and the `redis` package. Implies `--docker`. | off | Available |
| `--with-minio` | Add an S3-compatible object store (MinIO API) and the `minio` package. Implies `--docker`. See the note on the image in [Services](#services). | off | Available |
| `--with-mail` | Add Mailpit, a local mail catcher (SMTP + web UI). Implies `--docker`; Django settings are wired to it. | off | Available |
| `--traefik` | Route the app and the web UIs through an existing Traefik. Implies `--docker`. See [Traefik](#traefik). | off | Available |
| `--traefik-domain` | Base domain of the Traefik host names. Needs `--traefik`. | *config* (`localhost`) | Available |
| `--force` | Allow an existing target directory. Nothing is deleted; `uv init` still refuses if a `pyproject.toml` is already there. | off | Available |
| `--dry-run` | Validate and print the summary, then exit without writing anything. | off | Available |
| `--yes`, `-y` | Do not ask for confirmation. | off | Available |

### `kickoff add`

```bash
kickoff add <feature> [--path DIR] [--dbt-adapter A] [--traefik-domain D] [--dry-run] [--yes]
```

Adds a feature to a project that kickoff created (run it inside the project or pass `--path`).
Features: `prefect`, `dbt`, `docker`, `pgadmin`, `redis`, `minio`, `mail`, `traefik`. A database
(`--db`) cannot be added later because it changes the application settings; create a new project or
edit the files yourself. `kickoff add` needs the `.kickoff.toml` file (see below), so it only works on
projects created with kickoff 0.4 or later.

What it does, and what it deliberately does not:

- Computes a plan first and prints it (`--dry-run` stops there).
- **Creates** files that do not exist yet; **replaces** a generated file only when it is still
  byte-for-byte what kickoff generated before (so your edits are never lost); when you changed a file
  that the feature also needs to change, it writes the new version next to it as `<name>.kickoff-new`
  for you to merge. A file the feature does not touch is left alone.
- Runs `uv add` for the new packages, creates new folders, appends missing variables to `.env` and
  `.env.example` (existing values are never changed; if a value should change, e.g. Django's allowed
  hosts for Traefik, it tells you), appends missing `.gitignore` lines, and updates `.kickoff.toml`.
- Does **not** rewrite `README.md` or `AGENTS.md` (you may have edited them) and does not commit.
  It prints the commands and badge snippets you can paste in.

### `kickoff templates`

Lists the built-in and [custom](#custom-templates) templates with their source; custom files with
errors are listed as ignored, with the reason.

### `kickoff config`

| Command | Description | Status |
|---|---|---|
| `kickoff config show` | Print the effective configuration (file merged over defaults) as JSON. | Available |
| `kickoff config init` | Create `~/.config/kickoff/config.toml` containing the built-in defaults. Does nothing if it exists. | Available |
| `kickoff config path` | Print the path of the config file. | Available |
| `kickoff config edit` | Open the config in `$VISUAL` / `$EDITOR` (created with the defaults if missing), then check it: invalid TOML is an error, unknown or invalid values are warnings. | Available |
| `kickoff config set <key> <value>` | Change one value, e.g. `kickoff config set defaults.python_version 3.13`. Only known keys are accepted; the value is converted to the key's type (`true`/`false`, numbers) and checked (allowed choices, port range, existing template). Comments and layout of the file are kept. | Available |

## Templates

### `default`

Generic Python projects (data engineering, scripts, libraries): `src/<package>/`, `tests/`, `docs/`,
`scripts/`, `img/`, `data/{raw,interim,processed}/`. Dependencies: `typer`; dev: `ruff`, `vulture`, `pytest`,
`pytest-cov`, `pre-commit`, `pip-audit`.

### `django`

The default template plus a runnable Django project (ASGI) with SQLite:

- `manage.py` at the repository root; the project package in `src/<package>/` (settings, urls,
  asgi, wsgi) and a `core` app in `src/core/` with a home view, `templates/`, `static/`, `media/`.
- Settings read `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (`1`/`0`) and `DJANGO_ALLOWED_HOSTS` from the
  environment; the built-in defaults are for local development only. kickoff writes them to `.env`
  (with a freshly generated secret key) and `.env.example` (placeholders). Django does not read
  `.env` by itself, so the documented commands use `uv run --env-file .env ...`. `uv` fails when
  that file is missing, so after cloning run `cp .env.example .env`. CI and pytest do not need
  `.env`.
- Dependencies: `django`, `typer` and the server (`uvicorn`, or `gunicorn` with
  `--server gunicorn`). Dev: the default set plus `pytest-django`, `django-stubs`,
  `django-stubs-ext`, `factory-boy`.
- Ruff adds the `DJ` rules, `known-first-party = ["<package>", "core"]` and ignores `N999` in
  migrations; pytest gets `DJANGO_SETTINGS_MODULE`.
- CI adds `manage.py check --deploy` and `makemigrations --check --dry-run`.
- Run it: `uv run --env-file .env python manage.py migrate && uv run --env-file .env uvicorn <package>.asgi:application --app-dir src --reload`.

The Django files are written by kickoff itself (plain Python strings, no `django-admin`), which is
what makes the `src/` layout and the offline tests possible. A test run with a real Django install
is still the best check after each Django release.

### `jupyter`

Exploration and prototyping with JupyterLab and Polars. Folders: `notebooks/`, `src/<package>/`,
`data/`, `outputs/` (gitignored), `img/` and `tests/` (there is no `docs/` or `scripts/`).
Dependencies: `jupyterlab`, `ipykernel`, `polars`, `typer`; dev: `ruff`, `vulture`, `pytest`,
`nbval`, `pre-commit`, `pip-audit`.

- `notebooks/smoke.ipynb` is a minimal notebook that CI executes with `nbval --nbval-lax` (every
  cell must run without error; stored outputs are not compared). Notebooks are tracked in git.
- Ruff ignores `E402`, `F401`, `F403`, `F405` in `*.ipynb` files, and CI lints and format-checks
  everything **except** notebooks (`--exclude "*.ipynb"`).
- Run it: `uv run jupyter lab`. In Docker the container runs JupyterLab on port 8888, protected by
  the generated `JUPYTER_TOKEN` in `.env`.

## Custom templates

Put a TOML file in `<config dir>/templates/` (usually `~/.config/kickoff/templates/`; `kickoff
config path` shows the config dir) and use it with `kickoff new --template <file name>`. The file name
(without `.toml`) is the template name: lowercase letters, digits and dashes, and not the name of a
built-in template. No code is involved: a custom template **extends** a built-in one.

```toml
# ~/.config/kickoff/templates/api.toml
extends = "django"                    # default and jupyter work too; default if omitted
description = "Django with an API layer"      # replaces the base description

dependencies = ["httpx"]              # everything below is ADDED to the base template
dev_dependencies = ["hypothesis"]
ruff_select_extra = ["ASYNC"]
ci_jobs = []                          # extra CI steps; known: lint, format, test, vulture,
                                      #   notebooks, django-check, django-migrations
ignored_directories = ["tmp"]         # gitignored, contents kept out
gitignore_extra = [".cache/"]
stack_notes = ["Internal API"]        # lines in AGENTS.md "Stack"
testing_notes = ["Use hypothesis for property tests"]
badges = ["redis"]                    # keys of TOOL_BADGES in generators/badges.py

[directories]                         # path = comment shown in the trees ("" = not listed)
"src/{package}/api" = "HTTP API"

[commands]                            # shown in the README and AGENTS.md
"Run API" = "uv run uvicorn {package}.api:app"

[env_vars]                            # .env and .env.example
API_KEY = "change-me"

[ruff_per_file_ignores]
"scripts/**" = ["T201"]

[files]                               # extra files; __PACKAGE__ and __NAME__ are replaced
"src/__PACKAGE__/api/__init__.py" = ""
```

Rules and limits:

- Lists and tables are merged with the base; scalars (`description`) replace it. You cannot remove
  something the base template provides.
- Unknown keys, wrong types, unknown `ci_jobs` or `badges`, an unknown `extends`, bad names or a
  name clash with a built-in template make the file invalid. `kickoff templates` lists invalid files
  with the reason, `kickoff new` refuses to use them, and they never break the other templates.
- Custom templates cannot define servers, Docker commands or Python code; for those, extend a built-in
  template with files and commands, or add a template to kickoff itself.
- Every project records its template name in `.kickoff.toml`; `kickoff add` needs that template to
  still exist.

## GitHub

Before anything is written, kickoff checks that `gh` is installed and authenticated. If it is not,
GitHub is skipped with a warning (and the README gets static badges instead of repository-bound
ones). Otherwise, after the first commit and the hook installation, it runs
`gh repo create [owner/]<name> --source=. --remote=origin --description <template description>
--public|--private [--push]`.

- `owner` is `user.github_username` from the config when set; otherwise the account `gh` is
  authenticated as (`gh api user`).
- A missing or unauthenticated `gh`, or a failed `gh repo create` (for example the repository
  already exists) is a **warning**: the local project is complete and kickoff exits successfully.
- `--no-git` implies no GitHub repository.

## Docker and databases

Enabled by `--docker` or by any `--db` other than `none`; works with every template.

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-stage. The builder installs the locked production dependencies with uv (`--frozen --no-dev`, environment in `/opt/venv`); the runtime image is `python:<version>-slim` and runs as the non-root user `app`. `django`: an entrypoint runs `migrate` and `collectstatic`, plus a `HEALTHCHECK` on `/`, and the server is the one from `--server`. `jupyter`: JupyterLab on port 8888. `default`: `python -m <package>` (kickoff generates a small Typer `__main__.py` for that). |
| `docker-compose.yml` | Project name = package name. Services below. |
| `compose.override.yml` | Development settings, loaded automatically: code mounted at `/app`, auto-reload (Django), debug port, pgAdmin on loopback. The app runs as root there because bind-mounted files keep your user's ownership. For a production-like run use `docker compose -f docker-compose.yml ...`. |
| `.dockerignore` | Keeps `.git`, `.venv`, `.env`, `data/`, ... out of the image. |
| `docker/entrypoint.sh` | Django only. |
| `.env`, `.env.example` | Variables below. |
| `.opencode/skills/docker-workflow/SKILL.md` | Compose commands and ports, unless `--no-opencode`. |

**Services and profiles.** `db` (`postgres:16-alpine`, or `postgis/postgis:16-3.4` with
`--db postgis`; health-checked; data in the `pgdata` volume) and `pgadmin` (`dpage/pgadmin4`) have no
profile, so `docker compose up -d` starts only them. The `app` service is under the profile `full`:
`docker compose --profile full up --build`. Without a database there is nothing to start first, so
`app` has no profile and `docker compose up --build` starts it.

**Ports.**

| What | Host port | Default behaviour |
|---|---|---|
| app | `APP_PORT` (`--app-port`) to the container port (8000; Jupyter 8888) | published on all interfaces |
| database | `DB_PORT` (`--db-port`) | **not published**; other containers reach it as `db:5432`. `--expose-db` publishes it on `127.0.0.1` only, for DBeaver and similar tools |
| pgAdmin | `PGADMIN_PORT` (5050) | not published in `docker-compose.yml`; `compose.override.yml` publishes it on `127.0.0.1` only |
| debugger | `DEBUG_PORT` (5678) | `compose.override.yml`, `127.0.0.1` only; nothing listens until you start a debugger |

Nothing except the app is reachable from your local network, and several projects can run side by
side as long as their ports differ. Two deliberate differences from the original spec: exposed
ports are bound to `127.0.0.1`, and pgAdmin is reachable in development through the override file
(without a published port it would be unusable).

### Services

`--with-redis`, `--with-minio`, `--with-mail` and `--with-pgadmin` add compose services without a
profile (`docker compose up -d` starts them; the `app` is under the profile `full`). Each service is
one entry in `src/kickoff/features/services.py`.

| Service | Image | Reached by containers as | Development ports (127.0.0.1, `compose.override.yml`) | `.env` variables | Python package |
|---|---|---|---|---|---|
| Redis | `redis:7-alpine` | `redis:6379` (`REDIS_URL`) | `REDIS_PORT` 6379 | `REDIS_URL`, `REDIS_PORT` | `redis` |
| MinIO API | see below | `minio:9000` (`MINIO_ENDPOINT`) | `MINIO_API_PORT` 9000, `MINIO_CONSOLE_PORT` 9001 | `MINIO_ROOT_USER` (package name), `MINIO_ROOT_PASSWORD` (random), `MINIO_ENDPOINT`, the ports | `minio` |
| Mailpit | `axllent/mailpit:latest` | `mailpit:1025` (`MAIL_HOST`, `MAIL_PORT`) | `MAIL_PORT` 1025, `MAIL_UI_PORT` 8025 | `MAIL_HOST`, `MAIL_PORT`, `MAIL_UI_PORT` | none |

Inside the `app` container the host names above replace `localhost` (compose sets them), so the same
`.env` serves code on your machine and in Docker. The `app` waits for Redis to be healthy and for
MinIO and Mailpit to have started. With `--with-mail` the Django settings read `EMAIL_HOST` and
`EMAIL_PORT` from `MAIL_HOST` / `MAIL_PORT`.

**The MinIO image.** MinIO's own community images were withdrawn in 2026 (the repository is archived
and the Docker Hub and Quay images are gone). kickoff therefore uses **Silo**, the community fork
maintained by Pigsty, which keeps the S3 API, the `MINIO_*` variables and the data format
(`docker.io/pgsty/silo:RELEASE.2026-10-15T00-00-00Z`, pinned in `src/kickoff/defaults.py`). kickoff
prints a notice when you use it. Set `docker.minio_image` in the config to use any other image that
speaks the same protocol.

### Traefik

`--traefik` is for a home lab (or server) where **one Traefik instance, started separately, routes
many projects by host name**. kickoff does not run Traefik; it makes the project's compose file
Traefik-ready:

- The `app` (and the web UIs of pgAdmin, MinIO's console and Mailpit) join the **external** Docker
  network `traefik` and get Traefik labels. Create the network once with `docker network create
  traefik` and attach your Traefik to it.
- **No host port is published for the app**, so projects never collide on 8000; `--app-port` has no
  effect. The database still follows the usual rule (internal unless `--expose-db`).
- Host names: `<project>.<domain>` for the app and `<service>.<project>.<domain>` for the UIs
  (`pgadmin.`, `minio.`, `mail.`). The domain is `--traefik-domain` or `docker.traefik_domain`
  (default `localhost`, which modern browsers resolve to 127.0.0.1). Underscores in the project name
  become dashes because Django rejects host names with underscores.
- Entry point `docker.traefik_entrypoint` (default `web`). Set `docker.traefik_cert_resolver` (e.g.
  `letsencrypt`) and the routers also get `tls=true` and that resolver; the entry point is then usually
  `websecure`. Network name: `docker.traefik_network` (default `traefik`).
- Django: the host is added to `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` is set (http and
  https), and `SECURE_PROXY_SSL_HEADER` trusts Traefik's `X-Forwarded-Proto`. Only enable the header
  when requests really reach the app through a proxy you control.
- Run: `docker compose --profile full up -d --build`, then open `http://<project>.<domain>`.

Like the rest of the Docker support, the labels follow Traefik's documented Docker provider syntax but
are not tested against a running Traefik here; check the dashboard once.

**Variables** (`.env` has real values and is gitignored; `.env.example` shows placeholders):

| Variable | Value |
|---|---|
| `APP_PORT` | `--app-port` |
| `POSTGRES_USER`, `POSTGRES_DB` | the project's package name |
| `POSTGRES_PASSWORD` | `--db-password`, otherwise a random value (`change-me` in `.env.example`) |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `localhost` and `5432`, or `--db-port` with `--expose-db`; this is what code on your machine uses, compose points the `app` container at `db:5432` |
| `DB_PORT` | only with `--expose-db` |
| `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`, `PGADMIN_PORT` | only with `--with-pgadmin` (random password) |
| `DEBUG_PORT` | 5678 |
| `JUPYTER_TOKEN` | `jupyter` template only (random) |
| `REDIS_*`, `MINIO_*`, `MAIL_*` | the services above |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Django with `--traefik` |

The original spec derives *all* database values from the project name. kickoff derives the user and
database name that way but generates the password, so a predictable password never sits in a
database you may later expose.

**Django and the database**

- `--db postgres` adds `psycopg[binary]`. Settings use PostgreSQL when `POSTGRES_DB` is set (from
  `.env` through `--env-file`, from compose, and in CI) and SQLite otherwise, so `uv run pytest`
  works on a machine that cannot reach the database. To run `manage.py` against the container from
  your machine use `--expose-db`, or run the app in Docker.
- `--db postgis` uses `django.contrib.gis.db.backends.postgis` and adds `django.contrib.gis` to
  `INSTALLED_APPS`, with **no** SQLite fallback. Django's GIS support needs GDAL and GEOS: kickoff
  installs them in the image and in CI, and warns that you need them locally to run outside Docker.
- CI gets a PostgreSQL (or PostGIS) service with a throwaway password for the test job.
- Other templates only get the database container; their code does not use it. With `--with-dbt
  --dbt-adapter postgres` the dbt variables point at this database.

**Caveats**

- kickoff's tests parse the generated YAML and check the contents, but no image is built and no
  container is started during generation. Run `docker compose --profile full up --build` once on a
  new project.
- The Django container collects static files but does not serve them (uvicorn does not); add
  WhiteNoise or a reverse proxy for production.
- `ghcr.io/astral-sh/uv` and `dpage/pgadmin4` use the `latest` tag. Pin versions in
  `src/kickoff/defaults.py` when you need reproducible builds.

## Features

Features are optional and combine with any template (and with each other). They add folders,
dependencies, commands, `.env` variables, `.gitignore` entries, README badges and `AGENTS.md`
notes to the template you chose.

### Prefect (`--with-prefect`)

- Dependency: `prefect`.
- `src/<package>/flows/hello.py`: an example flow with one task. The greeting logic is a plain
  function, so `tests/test_flows.py` tests it without a Prefect server.
- `prefect.yaml` with one deployment (`hello`, entrypoint `src/<package>/flows/hello.py:hello_flow`,
  work pool `default`). The file is named `prefect.yaml` because that is the name `prefect deploy`
  looks for; Prefect's docs only mention `prefect.yaml` (use `prefect deploy --prefect-file` for any
  other name). `pull` is `null`, so Prefect asks how workers should get your code the first time
  you deploy (local directory, git clone, ...).
- `.prefectignore`.

```bash
uv run python src/<package>/flows/hello.py                  # run the flow locally
uv run prefect server start                                 # local API + UI
uv run prefect work-pool create default --type process      # once
uv run prefect worker start --pool default                  # keeps running
uv run prefect deploy --all                                 # create the deployments
```

### dbt (`--with-dbt`, `--dbt-adapter`)

- Adapter package from the table below (it installs `dbt-core` too).
- `dbt/` with `dbt_project.yml`, `profiles.yml`, an example model plus `schema.yml` (unique and
  not-null tests), and empty `analyses/ macros/ seeds/ snapshots/ tests/` folders.
- `profiles.yml` holds no secrets: every credential is read with `env_var(...)` from `.env`
  (`.env.example` lists the same variables).
- dbt must be run **from the repository root**, with explicit directories, through `uv run
  --env-file .env` (these are the commands kickoff writes in the README and `AGENTS.md`):

```bash
uv run --env-file .env dbt debug --project-dir dbt --profiles-dir dbt   # check the connection
uv run --env-file .env dbt build --project-dir dbt --profiles-dir dbt   # seeds + models + tests
```

- `.gitignore` gets `dbt/target/`, `dbt/dbt_packages/`, `dbt/logs/` and `dbt/.user.yml`.

| Adapter | Package | Maintainer | Environment variables (defaults in `.env`) | Notes |
|---|---|---|---|---|
| `postgres` | `dbt-postgres` | dbt Labs | `DBT_POSTGRES_HOST` (`localhost`), `_PORT` (`5432`), `_USER` and `_DBNAME` (project package name), `_PASSWORD` (`change-me`), `_SCHEMA` (`public`) | Needs a running Postgres; edit `.env` to match it. |
| `duckdb` | `dbt-duckdb` | community | `DBT_DUCKDB_PATH` (`data/processed/<package>.duckdb`) | No server needed. The path is relative to where dbt runs, hence "run from the repository root". Default adapter. |
| `sqlite` | `dbt-sqlite` | community | `DBT_SQLITE_PATH` (`data/processed/<package>.db`), `DBT_SQLITE_DIR` (`data/processed`) | dbt Labs does not support this plugin and its versions track dbt-core closely, so it may lag. kickoff prints a warning when you pick it. Only one writer thread (`threads: 1`). |

**Adding a warehouse (BigQuery, Snowflake, ...)** is one new entry in `ADAPTERS` in
`src/kickoff/features/dbt_adapters.py`: the pip package, the `dev` output lines of `profiles.yml`,
the environment variables, and a badge key in `TOOL_BADGES`. Nothing else changes.

**Caveats**

- kickoff writes these files from the Prefect and dbt documentation and its own tests only parse
  them; nobody runs dbt or Prefect during generation. Run `dbt debug` once after creating a project.
- A newer Python than an adapter supports can make `uv add` fail to resolve. If that happens, use
  `--python 3.12`.
- dbt and Prefect are not part of `ci.yml` (dbt needs warehouse credentials, Prefect a server).
  `dbt parse` is a good first CI step once you decide how to provide credentials.
- With `--db postgres|postgis` and `--dbt-adapter postgres`, the dbt Postgres variables point at
  the Docker database (run dbt on your machine with `--expose-db`).

## Workflows

| File | Runs | Does |
|---|---|---|
| `ci.yml` | on push and pull request to the default branch | `uv sync --all-groups`, Ruff lint and format check, pytest, Vulture. Django adds the system check, a missing-migrations check and, with `--db`, a PostgreSQL/PostGIS service (plus GDAL for PostGIS). Jupyter lints without notebooks and runs the smoke notebook with nbval. Python matrix: every supported version from `--python` upwards. |
| `security.yml` | every Monday 00:00 UTC (`0 0 * * 1`) and on demand (`workflow_dispatch`) | `uv run pip-audit` on the project's dependencies. It is separate from `ci.yml` so a newly published advisory never blocks an unrelated pull request. |

## Environment files

`.env` is gitignored; `.env.example` is committed and lists the same variables with placeholders.
The `default` template has no variables, so both files only contain a comment. The Django template
defines `DJANGO_SECRET_KEY` (random in `.env`, `change-me` in `.env.example`), `DJANGO_DEBUG` and
`DJANGO_ALLOWED_HOSTS`. Docker and the features add theirs (see [Docker and
databases](#docker-and-databases), dbt). A template or feature declares its variables once
(`env_vars`, with `env_examples` for placeholders).

## README badges

Only badges that apply to the generated project are included, in this order:

| Badge | When | Source |
|---|---|---|
| Python | always | With a public, pushed GitHub repo: dynamic, reads `requires-python` from `pyproject.toml` on GitHub (never stale). Otherwise static, from `--python` (`3.12+`). |
| CI, Security | public, pushed GitHub repo and CI enabled | GitHub Actions status of `ci.yml` / `security.yml` |
| Ruff, uv | always | Official Astral endpoint badges |
| Django | `django` template | Static badge |
| Jupyter, Polars | `jupyter` template | Static badges |
| Docker | `--docker` / `--db` | Static badge |
| PostgreSQL or PostGIS | `--db` | Static badge (dbt's PostgreSQL badge is not repeated) |
| Prefect | `--with-prefect` | Static badge |
| dbt and its adapter (DuckDB, PostgreSQL, SQLite) | `--with-dbt` | Static badges |
| License | unless `--license none` | With a public repo: detected by GitHub. Otherwise static from `--license`. |

"Public, pushed GitHub repo" means: git and GitHub enabled, `gh` usable, not `--private`, not
`--no-push`. Private repositories and unpushed repos get no repository-bound badges because those
images would not render. Codecov is not included yet (it needs an account and token; planned as an
opt-in). To add a tool badge, add one entry to `TOOL_BADGES` in `src/kickoff/generators/badges.py`
and list its key in the template's `badges`.

## Configuration

The config file lives at `$XDG_CONFIG_HOME/kickoff/config.toml` (usually
`~/.config/kickoff/config.toml`). Precedence: **command-line flag > config file > built-in default**.

| Key | Meaning | Used today |
|---|---|---|
| `defaults.template` | Template when `--template` is omitted. | Yes |
| `defaults.python_version` | Python version when `--python` is omitted. | Yes |
| `defaults.license` | License when `--license` is omitted. | Yes |
| `defaults.branch` | Git branch name; also used in CI triggers, `AGENTS.md` and the git-workflow skill. | Yes |
| `defaults.repo_visibility` | `public` or `private`. | Yes |
| `defaults.server` | `uvicorn` or `gunicorn` (Django). | Yes |
| `defaults.dbt_adapter` | Adapter when `--with-dbt` is used without `--dbt-adapter`. | Yes |
| `github.create_repo` | Create a GitHub repository by default. | Yes |
| `github.push_initial` | Push after creating it. | Yes |
| `user.name`, `user.email` | Author written to `pyproject.toml` and the MIT `LICENSE`. | Yes |
| `user.author_name_from_git` | If true, `git config --global user.name/email` fill in whatever `user.name/email` leave empty. | Yes |
| `user.github_username` | Owner used in `gh repo create owner/name`. | Yes |
| `docker.default_db` | Database when `--db` is omitted (`none`, `postgres`, `postgis`). | Yes |
| `docker.default_app_port`, `docker.default_db_port` | Host ports when `--app-port` / `--db-port` are omitted. | Yes |
| `docker.minio_image` | Image of the `--with-minio` service. | Yes |
| `docker.traefik_domain`, `docker.traefik_network`, `docker.traefik_entrypoint`, `docker.traefik_cert_resolver` | Traefik defaults, see [Traefik](#traefik). | Yes |

### Single source of truth

Every value that appears in more than one generated file (Python version, branch, Ruff rules, line
length, Vulture confidence, action versions, ...) is defined once in `src/kickoff/defaults.py`.
Directory layout is defined once per template or feature (`directories`) and the README, AGENTS.md,
skills, `.gitignore` sections and `.gitkeep` files are all derived from it. Tool versions (`ruff`,
`pytest`, ...) are not pinned anywhere: `uv add` resolves the latest release when a project is
created, and pre-commit runs Ruff through `uv run`, so the hooks always match the project's version.

## What gets generated

```text
my-project/
├── src/my_project/        # source code
├── tests/                 # includes a smoke test so the first CI run passes
├── docs/
├── scripts/
├── data/                  # raw / interim / processed, contents gitignored
├── img/                   # images and diagrams
├── Dockerfile             # --docker / --db (with docker-compose.yml, compose.override.yml,
├── .dockerignore          #   docker/entrypoint.sh for Django)
├── .kickoff.toml          # options used to create the project (read by `kickoff add`, no secrets)
├── pyproject.toml         # Ruff, Vulture and Pytest configured
├── .python-version
├── .env                   # gitignored; Django: generated secret key
├── .env.example           # committed template of .env
├── .pre-commit-config.yaml
├── .gitignore
├── LICENSE                # unless --license none
├── README.md
├── AGENTS.md              # unless --no-opencode
├── .opencode/skills/      # unless --no-opencode
├── prefect.yaml           # --with-prefect (plus src/<package>/flows/)
├── dbt/                   # --with-dbt
└── .github/workflows/      # unless --no-ci
    ├── ci.yml              # lint, format check, tests, vulture (+ Django checks)
    └── security.yml        # weekly pip-audit
```

Steps, in order: create folders → `uv init --bare` → write base files and template files → `LICENSE` →
enrich `pyproject.toml` → `uv add` dependencies → OpenCode files → CI and security workflows → `git init` + first
commit → install pre-commit hooks → create the GitHub repository. (The GitHub availability check
and owner lookup happen first, because the README badges depend on them.) On failure the partial result is
left in place (no rollback).

Notebooks are not part of any template; they will be an opt-in feature.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run vulture
```

Run `uv run pip-audit` locally to mimic the weekly security check.

`tests/test_defaults.py` fails if this repository's own Ruff / Vulture settings drift from
`defaults.py`. Features are plain `FeatureSpec` objects merged into the template by
`kickoff.features.apply_features`. License texts for Apache-2.0 and GPL-3.0 live in `src/kickoff/assets/licenses/`.

## Roadmap

| Version | Scope |
|---|---|
| v0.1 | `default` template, git, Ruff / Vulture / Pytest / pre-commit / pip-audit, AGENTS.md |
| v0.2 | `django` template (uvicorn / gunicorn), GitHub (`gh repo create`), `LICENSE`, Django CI checks |
| v0.2.1 | `img/`, `.env` / `.env.example`, weekly `security.yml` (audit leaves `ci.yml`), README badges |
| v0.2.2 | `--with-prefect` (flow, `prefect.yaml`), `--with-dbt` with `--dbt-adapter` (postgres, duckdb, sqlite; cloud adapters later) |
| v0.3 | `jupyter` template (Polars), Docker with PostgreSQL / PostGIS / pgAdmin (and the PostgreSQL CI service for Django), `docker-workflow` skill and per-template testing skill |
| v0.4 | `--with-redis`, `--with-minio` (Silo), `--with-mail` (Mailpit), `--traefik`, `kickoff config edit/set/path`, `kickoff add <feature>`, custom templates, `.kickoff.toml` |
| Ideas | cloud dbt adapters (BigQuery, Snowflake), `--codecov`, pinned image versions, `kickoff add db`, `kickoff upgrade` |
