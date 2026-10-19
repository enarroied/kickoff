"""Single source of truth for every default value used by kickoff.

Anything that appears in more than one place (Python version, branch name, Ruff
rules, line length, action versions, ...) lives here, so a future upgrade is a
one-line change instead of a hunt through the code base.
"""

from __future__ import annotations

# --- Project defaults -------------------------------------------------------
DEFAULT_TEMPLATE_NAME = "default"
DEFAULT_PYTHON_VERSION = "3.12"
SUPPORTED_PYTHON_VERSIONS = ("3.11", "3.12", "3.13")
DEFAULT_BRANCH = "master"
DEFAULT_LICENSE = "MIT"
SUPPORTED_LICENSES = ("MIT", "Apache-2.0", "GPL-3.0", "none")
# SPDX identifiers written to `project.license` in the generated pyproject.toml.
LICENSE_SPDX = {"MIT": "MIT", "Apache-2.0": "Apache-2.0", "GPL-3.0": "GPL-3.0-only"}
SUPPORTED_SERVERS = ("uvicorn", "gunicorn")
DEFAULT_VISIBILITY = "public"
DEFAULT_SERVER = "uvicorn"
DEFAULT_DBT_ADAPTER = "duckdb"
DEFAULT_DATABASE = "none"
SUPPORTED_DATABASES = ("none", "postgres", "postgis")
DEFAULT_APP_PORT = 8000
DEFAULT_DB_PORT = 5432

# Letters, digits, hyphens and underscores; must start with a letter.
PROJECT_NAME_PATTERN = r"^[A-Za-z][A-Za-z0-9_-]*$"

# --- Code quality tooling (written into every generated project) -------------
LINE_LENGTH = 100
RUFF_SELECT = ("E", "W", "F", "I", "UP", "PTH", "B", "C4", "SIM", "RET", "PL", "N")
RUFF_PER_FILE_IGNORES = {"tests/**": ("PLR2004",)}
VULTURE_MIN_CONFIDENCE = 80

# --- Docker / databases ---------------------------------------------------------
DB_IMAGES = {"postgres": "postgres:16-alpine", "postgis": "postgis/postgis:16-3.4"}
PGADMIN_IMAGE = "dpage/pgadmin4:latest"
PGADMIN_EMAIL = "admin@example.com"
PGADMIN_PORT = 5050  # host port, bound to 127.0.0.1 in compose.override.yml
DEBUG_PORT = 5678  # host port for a debugger, bound to 127.0.0.1 in compose.override.yml
UV_IMAGE = "ghcr.io/astral-sh/uv:latest"  # pin a version for reproducible image builds
DOCKER_USER = "app"

# Marks an environment variable whose value is generated randomly in `.env`
# (and shown as a placeholder in `.env.example`).
ENV_SECRET = "<generate-secret>"

# --- Third-party pins used by generated files --------------------------------
# Tool versions themselves (ruff, pytest, ...) are NOT pinned here: `uv add`
# resolves the latest release and records it in the generated pyproject.toml.
PRECOMMIT_HOOKS_REPO = "https://github.com/pre-commit/pre-commit-hooks"
PRECOMMIT_HOOKS_REV = "v4.6.0"  # bump with `pre-commit autoupdate`
ACTION_CHECKOUT = "actions/checkout@v4"
ACTION_SETUP_UV = "astral-sh/setup-uv@v6"

# --- Auxiliary services (--with-redis / --with-minio / --with-mail) -------------
REDIS_IMAGE = "redis:7-alpine"
# MinIO's own community images were withdrawn in 2026 (the repository is archived). Silo, the
# community fork maintained by Pigsty, is a drop-in replacement: same S3 API, same MINIO_*
# variables. Override with `docker.minio_image` in the config.
MINIO_IMAGE = "docker.io/pgsty/silo:RELEASE.2026-10-15T00-00-00Z"
MAILPIT_IMAGE = "axllent/mailpit:latest"

# --- Traefik (--traefik) ----------------------------------------------------------
DEFAULT_TRAEFIK_DOMAIN = "localhost"  # *.localhost resolves to 127.0.0.1 in modern browsers
DEFAULT_TRAEFIK_NETWORK = "traefik"  # external Docker network your Traefik instance is on
DEFAULT_TRAEFIK_ENTRYPOINT = "web"
DEFAULT_TRAEFIK_CERT_RESOLVER = ""  # empty: no TLS labels
