"""Global configuration loading for kickoff."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from kickoff import defaults

DEFAULT_CONFIG: dict[str, Any] = {
    "user": {
        "name": "",
        "email": "",
        "github_username": "",
        "author_name_from_git": True,
    },
    "defaults": {
        "template": defaults.DEFAULT_TEMPLATE_NAME,
        "branch": defaults.DEFAULT_BRANCH,
        "python_version": defaults.DEFAULT_PYTHON_VERSION,
        "license": defaults.DEFAULT_LICENSE,
        "repo_visibility": defaults.DEFAULT_VISIBILITY,
        "server": defaults.DEFAULT_SERVER,
        "dbt_adapter": defaults.DEFAULT_DBT_ADAPTER,
    },
    "docker": {
        "default_db": defaults.DEFAULT_DATABASE,
        "default_app_port": defaults.DEFAULT_APP_PORT,
        "default_db_port": defaults.DEFAULT_DB_PORT,
        "minio_image": defaults.MINIO_IMAGE,
        "traefik_domain": defaults.DEFAULT_TRAEFIK_DOMAIN,
        "traefik_network": defaults.DEFAULT_TRAEFIK_NETWORK,
        "traefik_entrypoint": defaults.DEFAULT_TRAEFIK_ENTRYPOINT,
        "traefik_cert_resolver": defaults.DEFAULT_TRAEFIK_CERT_RESOLVER,
    },
    "github": {
        "create_repo": True,
        "push_initial": True,
    },
}


def config_dir() -> Path:
    """Return the XDG config directory for kickoff."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "kickoff"


def config_path() -> Path:
    return config_dir() / "config.toml"


def load_config() -> dict[str, Any]:
    """Load global config, merged with defaults."""
    path = config_path()
    if not path.exists():
        return _deep_copy(DEFAULT_CONFIG)

    with path.open("rb") as f:
        user_config = tomllib.load(f)

    return _deep_merge(_deep_copy(DEFAULT_CONFIG), user_config)


def _deep_copy(d: dict[str, Any]) -> dict[str, Any]:
    return {k: (_deep_copy(v) if isinstance(v, dict) else v) for k, v in d.items()}


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base
