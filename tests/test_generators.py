"""Generator tests: no uv, git, gh or network needed."""

import tomllib
from pathlib import Path

import json

import yaml

from kickoff import defaults
from kickoff.features import apply_features
from kickoff.features.dbt_adapters import ADAPTERS
from kickoff.generators.badges import render_badges
from kickoff.generators.ci import generate_ci, python_matrix
from kickoff.generators.files import render_gitignore, write_base_files
from kickoff.generators.github import build_create_command
from kickoff.generators.licenses import render_license
from kickoff.generators.opencode import generate_opencode
from kickoff.generators.pyproject import enrich_pyproject
from kickoff.generators.structure import create_directories
from kickoff.models import ProjectSpec, TemplateSpec
from kickoff.templates.default_template import DEFAULT_TEMPLATE
from kickoff.templates import get_template
from kickoff.templates.django_template import DJANGO_TEMPLATE
from kickoff.templates.jupyter_template import JUPYTER_TEMPLATE


def make_spec(tmp_path: Path, **overrides) -> ProjectSpec:
    return ProjectSpec(name="demo-app", path=tmp_path, **overrides)


def generate_all(spec: ProjectSpec, template: TemplateSpec = DEFAULT_TEMPLATE) -> Path:
    create_directories(spec, template)
    write_base_files(spec, template)
    if spec.enable_opencode:
        generate_opencode(spec, template)
    if spec.enable_ci:
        generate_ci(spec, template)
    return spec.target_dir


def read(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def write_bare_pyproject(spec: ProjectSpec) -> Path:
    """What `uv init --bare` produces."""
    spec.target_dir.mkdir(parents=True, exist_ok=True)
    path = spec.target_dir / "pyproject.toml"
    path.write_text(
        '[project]\nname = "demo-app"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\ndependencies = []\n',
        encoding="utf-8",
    )
    return path


# --- default template -------------------------------------------------------


def test_structure_comes_from_template(tmp_path: Path) -> None:
    root = generate_all(make_spec(tmp_path))
    assert (root / "src" / "demo_app" / "__init__.py").is_file()
    assert (root / "tests" / "test_smoke.py").is_file()
    assert (root / "data" / "raw" / ".gitkeep").is_file()
    assert not (root / "notebooks").exists()
    assert not (root / "main.py").exists()
    assert not (root / "manage.py").exists()


def test_notebooks_are_not_mentioned_anywhere(tmp_path: Path) -> None:
    root = generate_all(make_spec(tmp_path))
    for generated in (".gitignore", "README.md", "AGENTS.md"):
        assert "notebooks" not in read(root, generated)


def test_python_version_and_branch_are_parameters(tmp_path: Path) -> None:
    root = generate_all(make_spec(tmp_path, python_version="3.13", branch="main"))
    agents = read(root, "AGENTS.md")
    ci = read(root, ".github/workflows/ci.yml")
    skill = read(root, ".opencode/skills/git-workflow/SKILL.md")
    assert "Python 3.13" in agents
    assert "3.12" not in agents
    assert read(root, ".python-version") == "3.13\n"
    assert 'python-version: ["3.13"]' in ci
    assert "branches: [main]" in ci
    assert "`main`" in agents
    assert "`main`" in skill


def test_python_matrix_starts_at_project_version() -> None:
    assert python_matrix("3.12") == ["3.12", "3.13"]
    assert python_matrix("3.11") == ["3.11", "3.12", "3.13"]


def test_enrich_pyproject_uses_shared_defaults(tmp_path: Path) -> None:
    spec = make_spec(tmp_path, author_name="Ada Lovelace", author_email="ada@example.com")
    path = write_bare_pyproject(spec)
    enrich_pyproject(spec, DEFAULT_TEMPLATE)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    assert tuple(data["tool"]["ruff"]["lint"]["select"]) == defaults.RUFF_SELECT
    assert data["tool"]["ruff"]["lint"]["per-file-ignores"]["tests/**"] == ["PLR2004"]
    assert data["tool"]["ruff"]["target-version"] == "py312"
    assert data["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]
    assert data["project"]["readme"] == "README.md"
    assert data["project"]["license"] == "MIT"
    assert data["project"]["authors"] == [{"name": "Ada Lovelace", "email": "ada@example.com"}]


# --- license ----------------------------------------------------------------


def test_mit_license_uses_author_and_current_year(tmp_path: Path) -> None:
    text = render_license(make_spec(tmp_path, author_name="Ada Lovelace"))
    assert text is not None
    assert text.startswith("MIT License")
    assert "Ada Lovelace" in text


def test_mit_license_falls_back_without_author(tmp_path: Path) -> None:
    text = render_license(make_spec(tmp_path))
    assert text is not None
    assert "demo-app contributors" in text


def test_bundled_licenses_and_none(tmp_path: Path) -> None:
    apache = render_license(make_spec(tmp_path, license="Apache-2.0"))
    gpl = render_license(make_spec(tmp_path, license="GPL-3.0"))
    assert apache is not None
    assert "Apache License" in apache
    assert gpl is not None
    assert "GNU GENERAL PUBLIC LICENSE" in gpl
    assert render_license(make_spec(tmp_path, license="none")) is None


# --- GitHub -----------------------------------------------------------------


def test_github_command_public_with_push(tmp_path: Path) -> None:
    command = build_create_command(make_spec(tmp_path), "A description")
    assert command[:4] == ["gh", "repo", "create", "demo-app"]
    assert "--public" in command
    assert "--private" not in command
    assert "--push" in command
    assert command[command.index("--description") + 1] == "A description"


def test_github_command_private_no_push_with_owner(tmp_path: Path) -> None:
    spec = make_spec(tmp_path, private=True, push_initial=False, github_owner="ada")
    command = build_create_command(spec, "x")
    assert command[3] == "ada/demo-app"
    assert "--private" in command
    assert "--push" not in command


# --- django template --------------------------------------------------------


def generate_django(tmp_path: Path, **overrides) -> Path:
    spec = make_spec(tmp_path, template="django", **overrides)
    return generate_all(spec, DJANGO_TEMPLATE)


def test_django_skeleton_is_created(tmp_path: Path) -> None:
    root = generate_django(tmp_path)
    for relative in (
        "manage.py",
        "src/demo_app/settings.py",
        "src/demo_app/urls.py",
        "src/demo_app/asgi.py",
        "src/demo_app/wsgi.py",
        "src/core/apps.py",
        "src/core/views.py",
        "src/core/migrations/__init__.py",
        "templates/home.html",
        "tests/test_core.py",
        "static/.gitkeep",
        "media/.gitkeep",
    ):
        assert (root / relative).is_file(), relative


def test_django_files_have_no_placeholders_and_valid_syntax(tmp_path: Path) -> None:
    root = generate_django(tmp_path)
    for generated in root.rglob("*"):
        if generated.is_file() and ".opencode" not in generated.parts:
            assert "__PACKAGE__" not in generated.read_text(encoding="utf-8"), generated
            assert "__NAME__" not in generated.read_text(encoding="utf-8"), generated
    for source in root.rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
    settings = read(root, "src/demo_app/settings.py")
    assert 'ROOT_URLCONF = "demo_app.urls"' in settings
    assert 'DJANGO_SETTINGS_MODULE", "demo_app.settings"' in read(root, "manage.py")


def test_django_gitignore_and_ci(tmp_path: Path) -> None:
    root = generate_django(tmp_path)
    gitignore = read(root, ".gitignore")
    assert "media/**" in gitignore
    assert "db.sqlite3" in gitignore
    ci = read(root, ".github/workflows/ci.yml")
    assert "manage.py check --deploy" in ci
    assert "makemigrations --check --dry-run" in ci


def test_django_agents_and_readme_document_server(tmp_path: Path) -> None:
    root = generate_django(tmp_path)
    agents = read(root, "AGENTS.md")
    assert "uvicorn demo_app.asgi:application --app-dir src --reload" in agents
    assert "manage.py migrate" in agents
    assert "src/core/" in agents
    assert "uvicorn demo_app.asgi:application" in read(root, "README.md")


def test_django_gunicorn_server(tmp_path: Path) -> None:
    root = generate_django(tmp_path, server="gunicorn")
    assert "gunicorn demo_app.wsgi:application --chdir src" in read(root, "AGENTS.md")
    assert "uvicorn" not in read(root, "AGENTS.md").split("## Commands")[1]


def test_django_enrich_pyproject(tmp_path: Path) -> None:
    spec = make_spec(tmp_path, template="django")
    path = write_bare_pyproject(spec)
    enrich_pyproject(spec, DJANGO_TEMPLATE)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    lint = data["tool"]["ruff"]["lint"]
    assert lint["select"][-1] == "DJ"
    assert lint["isort"]["known-first-party"] == ["demo_app", "core"]
    assert lint["per-file-ignores"]["**/migrations/*.py"] == ["N999"]
    assert lint["per-file-ignores"]["tests/**"] == ["PLR2004"]
    ini = data["tool"]["pytest"]["ini_options"]
    assert ini["DJANGO_SETTINGS_MODULE"] == "demo_app.settings"
    assert ini["pythonpath"] == ["src"]


def test_default_gitignore_has_no_django_entries() -> None:
    gitignore = render_gitignore(DEFAULT_TEMPLATE)
    assert "media" not in gitignore
    assert "db.sqlite3" not in gitignore


# --- v0.2.1: img/, env files, security workflow, badges ---------------------


def test_img_directory_exists_in_every_template(tmp_path: Path) -> None:
    default_root = generate_all(make_spec(tmp_path / "a"))
    django_root = generate_django(tmp_path / "b")
    for root in (default_root, django_root):
        assert (root / "img" / ".gitkeep").is_file()
        assert "img/" in read(root, "README.md")


def test_env_files_for_default_template(tmp_path: Path) -> None:
    root = generate_all(make_spec(tmp_path))
    assert read(root, ".env") == read(root, ".env.example")
    assert "=" not in read(root, ".env")
    assert "cp .env.example .env" not in read(root, "README.md")


def test_env_files_for_django_generate_a_real_secret(tmp_path: Path) -> None:
    first = generate_django(tmp_path / "a")
    second = generate_django(tmp_path / "b")
    env = dict(line.split("=", 1) for line in read(first, ".env").splitlines() if "=" in line)
    other = dict(line.split("=", 1) for line in read(second, ".env").splitlines() if "=" in line)
    assert len(env["DJANGO_SECRET_KEY"]) >= 50
    assert env["DJANGO_SECRET_KEY"] != other["DJANGO_SECRET_KEY"]
    assert defaults.ENV_SECRET not in read(first, ".env")
    assert env["DJANGO_DEBUG"] == "1"
    example = read(first, ".env.example")
    assert "DJANGO_SECRET_KEY=change-me" in example
    assert env["DJANGO_SECRET_KEY"] not in example
    assert "cp .env.example .env" in read(first, "README.md")
    assert "--env-file .env" in read(first, "README.md")


def test_security_workflow_replaces_audit_in_ci(tmp_path: Path) -> None:
    root = generate_all(make_spec(tmp_path, python_version="3.13"))
    ci = read(root, ".github/workflows/ci.yml")
    security = read(root, ".github/workflows/security.yml")
    assert "pip-audit" not in ci
    assert "cron: '0 0 * * 1'" in security
    assert "workflow_dispatch:" in security
    assert "uv run pip-audit" in security
    assert 'python-version: "3.13"' in security
    assert "Security audit" in read(root, "AGENTS.md")


def badges_for(tmp_path: Path, tmpl: TemplateSpec = DEFAULT_TEMPLATE, **overrides) -> str:
    return "\n".join(render_badges(make_spec(tmp_path, **overrides), tmpl))


def test_badges_without_github_repo(tmp_path: Path) -> None:
    badges = badges_for(tmp_path)
    assert "Python-3.12+" in badges
    assert "License-MIT-blue" in badges
    assert "ruff/main/assets/badge/v2.json" in badges
    assert "uv/main/assets/badge/v0.json" in badges
    assert "actions/workflows" not in badges
    assert "raw.githubusercontent.com/ada" not in badges
    assert "Django" not in badges


def test_badges_with_public_repo(tmp_path: Path) -> None:
    badges = badges_for(tmp_path, github_owner="ada", branch="main")
    assert "ada/demo-app/main/pyproject.toml" in badges
    assert "query=$.project.requires-python" in badges
    assert "github.com/ada/demo-app/actions/workflows/ci.yml/badge.svg" in badges
    assert "github.com/ada/demo-app/actions/workflows/security.yml/badge.svg" in badges
    assert "img.shields.io/github/license/ada/demo-app" in badges


def test_repo_badges_are_skipped_when_repo_is_not_public_and_pushed(tmp_path: Path) -> None:
    for overrides in ({"private": True}, {"push_initial": False}, {"create_github": False}):
        badges = badges_for(tmp_path, github_owner="ada", **overrides)
        assert "actions/workflows" not in badges, overrides
        assert "Python-3.12+" in badges, overrides


def test_badges_without_ci_or_license(tmp_path: Path) -> None:
    badges = badges_for(tmp_path, github_owner="ada", enable_ci=False, license="none")
    assert "actions/workflows" not in badges
    assert "License" not in badges


def test_license_badge_escapes_hyphens(tmp_path: Path) -> None:
    assert "License-Apache--2.0-blue" in badges_for(tmp_path, license="Apache-2.0")


def test_django_template_adds_its_badge(tmp_path: Path) -> None:
    badges = badges_for(tmp_path, DJANGO_TEMPLATE, template="django")
    assert "badge/Django-092E20?logo=django" in badges


def test_readme_starts_with_title_then_badges(tmp_path: Path) -> None:
    root = generate_all(make_spec(tmp_path))
    lines = read(root, "README.md").splitlines()
    assert lines[0] == "# demo-app"
    assert lines[2].startswith("![Python]")


# --- v0.2.2: Prefect and dbt features ---------------------------------------


def generate_with_features(
    tmp_path: Path, features: list[str], base: TemplateSpec = DEFAULT_TEMPLATE, **overrides
) -> tuple[ProjectSpec, TemplateSpec, Path]:
    spec = make_spec(tmp_path, features=features, **overrides)
    template = apply_features(base, spec)
    root = generate_all(spec, template)
    return spec, template, root


def test_no_features_leaves_template_untouched(tmp_path: Path) -> None:
    spec = make_spec(tmp_path)
    assert apply_features(DEFAULT_TEMPLATE, spec) == DEFAULT_TEMPLATE


def test_prefect_feature_files_and_merge(tmp_path: Path) -> None:
    _, template, root = generate_with_features(tmp_path, ["prefect"])
    assert "prefect" in template.dependencies
    assert "typer" in template.dependencies
    assert (root / "src/demo_app/flows/hello.py").is_file()
    assert (root / "tests/test_flows.py").is_file()
    assert (root / ".prefectignore").is_file()
    prefect_yaml = yaml.safe_load(read(root, "prefect.yaml"))
    assert prefect_yaml["name"] == "demo-app"
    deployment = prefect_yaml["deployments"][0]
    assert deployment["entrypoint"] == "src/demo_app/flows/hello.py:hello_flow"
    assert deployment["work_pool"]["name"] == "default"
    agents = read(root, "AGENTS.md")
    assert "prefect deploy --all" in agents
    assert "src/demo_app/flows/" in agents
    assert "badge/Prefect-F02D5E?logo=prefect" in read(root, "README.md")
    for source in root.rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")


def test_dbt_feature_files_for_every_adapter(tmp_path: Path) -> None:
    for adapter, info in ADAPTERS.items():
        spec, template, root = generate_with_features(
            tmp_path / adapter, ["dbt"], dbt_adapter=adapter
        )
        project = yaml.safe_load(read(root, "dbt/dbt_project.yml"))
        assert project["name"] == "demo_app"
        assert project["profile"] == "demo_app"
        profiles = yaml.safe_load(read(root, "dbt/profiles.yml"))
        output = profiles["demo_app"]["outputs"]["dev"]
        assert output["type"] == adapter
        assert profiles["demo_app"]["target"] == "dev"
        assert info.package in template.dependencies
        schema = yaml.safe_load(read(root, "dbt/models/schema.yml"))
        assert schema["models"][0]["name"] == "example"
        assert (root / "dbt/models/example.sql").is_file()
        assert (root / "dbt/seeds/.gitkeep").is_file()
        env = read(root, ".env")
        for name in info.env_vars:
            assert f"{name}=" in env
            assert f"{name}=" in read(root, ".env.example")
        readme = read(root, "README.md")
        assert "dbt/" in readme
        assert "cp .env.example .env" in readme
        assert "dbt build --project-dir dbt --profiles-dir dbt" in readme
        assert "--env-file .env dbt" in read(root, "AGENTS.md")
        gitignore = read(root, ".gitignore")
        assert "dbt/target/" in gitignore
        assert "__PACKAGE__" not in read(root, "dbt/profiles.yml")
        assert spec.dbt_adapter == adapter


def test_dbt_postgres_values_and_badges(tmp_path: Path) -> None:
    _, _, root = generate_with_features(tmp_path, ["dbt"], dbt_adapter="postgres")
    env = read(root, ".env")
    assert "DBT_POSTGRES_USER=demo_app" in env
    assert "DBT_POSTGRES_DBNAME=demo_app" in env
    assert "DBT_POSTGRES_PASSWORD=change-me" in env
    readme = read(root, "README.md")
    assert "badge/dbt-FF694B" in readme
    assert "badge/PostgreSQL-4169E1?logo=postgresql" in readme


def test_dbt_duckdb_badge_and_sqlite_notice(tmp_path: Path) -> None:
    _, _, duck_root = generate_with_features(tmp_path / "d", ["dbt"], dbt_adapter="duckdb")
    assert "badge/DuckDB-FFF?logo=duckdb&logoColor=374151" in read(duck_root, "README.md")
    _, sqlite_template, _ = generate_with_features(tmp_path / "s", ["dbt"], dbt_adapter="sqlite")
    assert any("community plugin" in notice for notice in sqlite_template.notices)
    _, duck_template, _ = generate_with_features(tmp_path / "e", ["dbt"], dbt_adapter="duckdb")
    assert duck_template.notices == []


def test_features_combine_with_django_and_each_other(tmp_path: Path) -> None:
    spec, template, root = generate_with_features(
        tmp_path, ["prefect", "dbt"], DJANGO_TEMPLATE, template="django"
    )
    assert "django" in template.dependencies
    assert {"prefect", "dbt-duckdb"} <= set(template.dependencies)
    assert (root / "manage.py").is_file()
    assert (root / "dbt/dbt_project.yml").is_file()
    assert (root / "prefect.yaml").is_file()
    env = read(root, ".env")
    assert "DJANGO_SECRET_KEY=" in env
    assert "DBT_DUCKDB_PATH=" in env
    assert spec.features == ["prefect", "dbt"]


def test_all_generated_yaml_is_valid(tmp_path: Path) -> None:
    _, _, root = generate_with_features(tmp_path, ["prefect", "dbt"], dbt_adapter="sqlite")
    for generated in list(root.rglob("*.yml")) + list(root.rglob("*.yaml")):
        if ".opencode" not in generated.parts:
            assert yaml.safe_load(generated.read_text(encoding="utf-8")) is not None, generated


# --- v0.3: jupyter template, Docker, databases ------------------------------


def generate_template(
    tmp_path: Path, name: str, features: tuple[str, ...] = (), **overrides
) -> tuple[ProjectSpec, TemplateSpec, Path]:
    spec = make_spec(tmp_path, template=name, features=list(features), **overrides)
    template = apply_features(get_template(name), spec)
    return spec, template, generate_all(spec, template)


def generate_docker(
    tmp_path: Path, name: str = "default", features: tuple[str, ...] = (), **overrides
) -> tuple[ProjectSpec, TemplateSpec, Path]:
    overrides.setdefault("db_password", "s3cret")
    return generate_template(tmp_path, name, (*features, "docker"), docker=True, **overrides)


def parse_env(root: Path, filename: str = ".env") -> dict[str, str]:
    lines = read(root, filename).splitlines()
    return dict(line.split("=", 1) for line in lines if "=" in line and not line.startswith("#"))


def test_jupyter_template_structure_and_notebook(tmp_path: Path) -> None:
    _, template, root = generate_template(tmp_path, "jupyter")
    expected = ("notebooks/smoke.ipynb", "outputs/.gitkeep", "img/.gitkeep", "tests/__init__.py")
    for relative in expected:
        assert (root / relative).is_file(), relative
    assert not (root / "docs").exists()
    assert not (root / "scripts").exists()
    notebook = json.loads(read(root, "notebooks/smoke.ipynb"))
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    assert {"jupyterlab", "ipykernel", "polars"} <= set(template.dependencies)
    assert "nbval" in template.dev_dependencies
    assert "pytest-cov" not in template.dev_dependencies


def test_jupyter_gitignore_tracks_notebooks_but_not_outputs(tmp_path: Path) -> None:
    _, _, root = generate_template(tmp_path, "jupyter")
    gitignore = read(root, ".gitignore")
    assert "outputs/**" in gitignore
    assert "data/**" in gitignore
    assert ".ipynb_checkpoints/" in gitignore
    assert "*.ipynb" not in gitignore


def test_jupyter_ci_skips_notebooks_in_lint_and_runs_nbval(tmp_path: Path) -> None:
    _, _, root = generate_template(tmp_path, "jupyter")
    ci = read(root, ".github/workflows/ci.yml")
    assert 'uv run ruff check . --exclude "*.ipynb"' in ci
    assert 'uv run ruff format --check . --exclude "*.ipynb"' in ci
    assert "uv run pytest --nbval-lax notebooks/smoke.ipynb" in ci
    yaml.safe_load(ci)
    agents = read(root, "AGENTS.md")
    assert "uv run jupyter lab" in agents
    testing = read(root, ".opencode/skills/testing/SKILL.md")
    assert "nbval" in testing
    assert "badge/Jupyter-F37626?logo=jupyter" in read(root, "README.md")


def test_jupyter_enrich_pyproject(tmp_path: Path) -> None:
    spec = make_spec(tmp_path, template="jupyter")
    path = write_bare_pyproject(spec)
    enrich_pyproject(spec, JUPYTER_TEMPLATE)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    ignores = data["tool"]["ruff"]["lint"]["per-file-ignores"]
    assert ignores["*.ipynb"] == ["E402", "F401", "F403", "F405"]
    assert ignores["tests/**"] == ["PLR2004"]


def test_docker_without_database_for_default_template(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path)
    compose = yaml.safe_load(read(root, "docker-compose.yml"))
    assert list(compose["services"]) == ["app"]
    assert "profiles" not in compose["services"]["app"]
    assert compose["services"]["app"]["ports"] == ["${APP_PORT:-8000}:8000"]
    assert "volumes" not in compose
    dockerfile = read(root, "Dockerfile")
    assert "ARG PYTHON_VERSION=3.12" in dockerfile
    assert 'CMD ["python", "-m", "demo_app"]' in dockerfile
    assert "ENTRYPOINT" not in dockerfile
    assert "HEALTHCHECK" not in dockerfile
    assert (root / "src/demo_app/__main__.py").is_file()
    assert not (root / "docker/entrypoint.sh").exists()
    assert parse_env(root)["APP_PORT"] == "8000"
    skill = read(root, ".opencode/skills/docker-workflow/SKILL.md")
    assert "docker compose up --build" in skill
    assert "Database" not in skill
    assert "docker compose up --build" in read(root, "AGENTS.md")
    assert "badge/Docker-2496ED?logo=docker" in read(root, "README.md")


def test_docker_without_opencode_skips_the_skill(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, enable_opencode=False)
    assert not (root / ".opencode").exists()
    assert (root / "Dockerfile").is_file()


def test_docker_postgres_keeps_database_internal(tmp_path: Path) -> None:
    spec, template, root = generate_docker(tmp_path, db="postgres", app_port=8100)
    compose = yaml.safe_load(read(root, "docker-compose.yml"))
    db = compose["services"]["db"]
    assert db["image"] == "postgres:16-alpine"
    assert db["expose"] == ["5432"]
    assert "ports" not in db
    assert db["healthcheck"]["test"][1].startswith("pg_isready")
    app = compose["services"]["app"]
    assert app["profiles"] == ["full"]
    assert app["depends_on"]["db"]["condition"] == "service_healthy"
    assert app["environment"]["POSTGRES_HOST"] == "db"
    assert app["ports"] == ["${APP_PORT:-8100}:8000"]
    assert "pgadmin" not in compose["services"]
    env = parse_env(root)
    assert env["POSTGRES_USER"] == "demo_app"
    assert env["POSTGRES_DB"] == "demo_app"
    assert env["POSTGRES_PASSWORD"] == "s3cret"
    assert env["APP_PORT"] == "8100"
    assert "DB_PORT" not in env
    assert parse_env(root, ".env.example")["POSTGRES_PASSWORD"] == "change-me"
    assert spec.docker


def test_docker_expose_db_binds_loopback_with_custom_port(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, db="postgres", expose_db=True, db_port=5433)
    compose = yaml.safe_load(read(root, "docker-compose.yml"))
    assert compose["services"]["db"]["ports"] == ["127.0.0.1:${DB_PORT:-5432}:5432"]
    env = parse_env(root)
    assert env["DB_PORT"] == "5433"
    assert env["POSTGRES_PORT"] == "5433"
    assert "published on 127.0.0.1:5433" in read(root, ".opencode/skills/docker-workflow/SKILL.md")


def test_docker_pgadmin_is_internal_in_compose_and_loopback_in_override(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, db="postgres", with_pgadmin=True)
    compose = yaml.safe_load(read(root, "docker-compose.yml"))
    pgadmin = compose["services"]["pgadmin"]
    assert pgadmin["image"] == defaults.PGADMIN_IMAGE
    assert "ports" not in pgadmin
    override = yaml.safe_load(read(root, "compose.override.yml"))
    assert override["services"]["pgadmin"]["ports"] == ["127.0.0.1:${PGADMIN_PORT:-5050}:80"]
    assert override["services"]["app"]["user"] == "root"
    env = parse_env(root)
    assert env["PGADMIN_DEFAULT_EMAIL"] == defaults.PGADMIN_EMAIL
    assert len(env["PGADMIN_DEFAULT_PASSWORD"]) >= 40
    assert parse_env(root, ".env.example")["PGADMIN_DEFAULT_PASSWORD"] == "change-me"


def test_docker_django_postgres(tmp_path: Path) -> None:
    _, template, root = generate_docker(tmp_path, "django", db="postgres")
    assert "psycopg[binary]" in template.dependencies
    dockerfile = read(root, "Dockerfile")
    assert 'ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]' in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "gdal-bin" not in dockerfile
    assert '"--port", "8000"]' in dockerfile
    assert "migrate --noinput" in read(root, "docker/entrypoint.sh")
    override = yaml.safe_load(read(root, "compose.override.yml"))
    assert override["services"]["app"]["command"][-1] == "--reload"
    settings = read(root, "src/demo_app/settings.py")
    assert 'if os.environ.get("POSTGRES_DB"):' in settings
    assert "django.db.backends.postgresql" in settings
    assert "db.sqlite3" in settings  # fallback for machines without the database
    assert "django.contrib.gis" not in settings
    ci = yaml.safe_load(read(root, ".github/workflows/ci.yml"))
    job = ci["jobs"]["quality"]
    assert job["services"]["postgres"]["image"] == "postgres:16-alpine"
    assert job["env"]["POSTGRES_HOST"] == "localhost"
    assert not any("GDAL" in step.get("name", "") for step in job["steps"])
    for source in root.rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")


def test_docker_django_postgis(tmp_path: Path) -> None:
    _, template, root = generate_docker(
        tmp_path, "django", db="postgis", expose_db=True, with_pgadmin=True
    )
    assert any("GDAL" in notice for notice in template.notices)
    settings = read(root, "src/demo_app/settings.py")
    assert "django.contrib.gis.db.backends.postgis" in settings
    assert '    "django.contrib.gis",' in settings
    assert "db.sqlite3" not in settings
    assert "gdal-bin" in read(root, "Dockerfile")
    ci = yaml.safe_load(read(root, ".github/workflows/ci.yml"))
    job = ci["jobs"]["quality"]
    assert job["services"]["postgres"]["image"] == "postgis/postgis:16-3.4"
    assert any("GDAL" in step.get("name", "") for step in job["steps"])
    assert "badge/PostGIS-336791?logo=postgresql" in read(root, "README.md")
    for source in root.rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")


def test_docker_django_gunicorn(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, "django", server="gunicorn")
    assert '"gunicorn", "demo_app.wsgi:application"' in read(root, "Dockerfile")
    assert '"0.0.0.0:8000"' in read(root, "Dockerfile")
    override = yaml.safe_load(read(root, "compose.override.yml"))
    assert override["services"]["app"]["command"][-1] == "--reload"


def test_docker_jupyter_uses_its_own_port_and_token(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, "jupyter")
    dockerfile = read(root, "Dockerfile")
    assert "EXPOSE 8888" in dockerfile
    assert '"--port=8888"' in dockerfile
    compose = yaml.safe_load(read(root, "docker-compose.yml"))
    assert compose["services"]["app"]["ports"] == ["${APP_PORT:-8000}:8888"]
    assert len(parse_env(root)["JUPYTER_TOKEN"]) >= 40
    assert parse_env(root, ".env.example")["JUPYTER_TOKEN"] == "change-me"


def test_docker_files_have_no_unresolved_placeholders(tmp_path: Path) -> None:
    _, _, root = generate_docker(
        tmp_path, "django", ("prefect", "dbt"), db="postgis", expose_db=True, with_pgadmin=True
    )
    for name in ("Dockerfile", "docker-compose.yml", "compose.override.yml", "AGENTS.md"):
        text = read(root, name)
        assert "{package}" not in text and "{port}" not in text, name
        assert "__PACKAGE__" not in text, name
    for name in ("docker-compose.yml", "compose.override.yml"):
        yaml.safe_load(read(root, name))


def test_dbt_postgres_points_at_the_docker_database(tmp_path: Path) -> None:
    _, _, root = generate_docker(
        tmp_path, features=("dbt",), db="postgres", expose_db=True, db_port=5433,
        dbt_adapter="postgres",
    )
    env = parse_env(root)
    assert env["DBT_POSTGRES_USER"] == env["POSTGRES_USER"] == "demo_app"
    assert env["DBT_POSTGRES_PASSWORD"] == env["POSTGRES_PASSWORD"] == "s3cret"
    assert env["DBT_POSTGRES_DBNAME"] == env["POSTGRES_DB"]
    assert env["DBT_POSTGRES_PORT"] == "5433"
    example = parse_env(root, ".env.example")
    assert example["DBT_POSTGRES_PASSWORD"] == "change-me"
    assert "badge/PostgreSQL-4169E1" in read(root, "README.md")
    assert read(root, "README.md").count("badge/PostgreSQL-4169E1") == 1
