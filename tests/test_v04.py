"""v0.4: auxiliary services, Traefik, manifest, `kickoff add`, custom templates."""

from pathlib import Path

import pytest
import yaml
from test_generators import (
    generate_docker,
    generate_template,
    make_spec,
    parse_env,
    read,
)

from kickoff import defaults
from kickoff.adding import SUFFIX, build_plan, write_manifest, write_plan
from kickoff.custom_templates import CustomTemplateError, build_template, load_custom_templates
from kickoff.exceptions import ValidationError
from kickoff.manifest import MANIFEST_NAME, read_manifest, render_manifest
from kickoff.registry import all_templates, get_template


def compose(root: Path) -> dict:
    return yaml.safe_load(read(root, "docker-compose.yml"))


# --- auxiliary services -------------------------------------------------------


def test_redis_service(tmp_path: Path) -> None:
    _, template, root = generate_docker(tmp_path, with_redis=True)
    services = compose(root)["services"]
    assert services["redis"]["image"] == defaults.REDIS_IMAGE
    assert services["redis"]["healthcheck"]["test"] == ["CMD", "redis-cli", "ping"]
    app = services["app"]
    assert app["profiles"] == ["full"]  # a service exists, so the app is opt-in
    assert app["depends_on"]["redis"]["condition"] == "service_healthy"
    assert app["environment"]["REDIS_URL"] == "redis://redis:6379/0"
    assert "redis" in template.dependencies
    assert compose(root)["volumes"] == {"redis": None}
    env = parse_env(root)
    assert env["REDIS_URL"] == "redis://localhost:6379/0"
    assert env["REDIS_PORT"] == "6379"
    override = yaml.safe_load(read(root, "compose.override.yml"))
    assert override["services"]["redis"]["ports"] == ["127.0.0.1:${REDIS_PORT:-6379}:6379"]
    assert "badge/Redis-DC382D?logo=redis" in read(root, "README.md")
    assert "redis" in read(root, ".opencode/skills/docker-workflow/SKILL.md")


def test_minio_service_uses_the_silo_image_and_warns(tmp_path: Path) -> None:
    _, template, root = generate_docker(tmp_path, with_minio=True)
    minio = compose(root)["services"]["minio"]
    assert minio["image"] == defaults.MINIO_IMAGE
    assert "silo" in defaults.MINIO_IMAGE
    assert minio["command"] == ["server", "/data", "--console-address", ":9001"]
    depends_on = compose(root)["services"]["app"]["depends_on"]
    assert depends_on["minio"]["condition"] == "service_started"
    env = parse_env(root)
    assert env["MINIO_ROOT_USER"] == "demo_app"
    assert len(env["MINIO_ROOT_PASSWORD"]) >= 40
    assert parse_env(root, ".env.example")["MINIO_ROOT_PASSWORD"] == "change-me"
    assert env["MINIO_API_PORT"] == "9000"
    assert env["MINIO_CONSOLE_PORT"] == "9001"
    assert any("Silo" in notice for notice in template.notices)
    assert "minio" in template.dependencies
    assert "badge/MinIO-C5A572" in read(root, "README.md")


def test_minio_image_can_be_overridden(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, with_minio=True, minio_image="example/s3:1")
    assert compose(root)["services"]["minio"]["image"] == "example/s3:1"


def test_mail_service_and_django_settings(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path / "dj", "django", with_mail=True)
    assert compose(root)["services"]["mailpit"]["image"] == defaults.MAILPIT_IMAGE
    assert compose(root)["services"]["app"]["environment"]["MAIL_HOST"] == "mailpit"
    settings = read(root, "src/demo_app/settings.py")
    assert 'EMAIL_HOST = os.environ.get("MAIL_HOST", "localhost")' in settings
    assert parse_env(root)["MAIL_UI_PORT"] == "8025"
    _, _, plain = generate_docker(tmp_path / "plain", "django")
    assert "EMAIL_HOST" not in read(plain, "src/demo_app/settings.py")
    for source in root.rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")


def test_services_with_database_wait_for_both(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, db="postgres", with_redis=True, with_mail=True)
    app = compose(root)["services"]["app"]
    assert set(app["depends_on"]) == {"db", "redis", "mailpit"}
    assert app["environment"]["POSTGRES_HOST"] == "db"
    assert app["environment"]["REDIS_URL"].startswith("redis://redis")


# --- Traefik ----------------------------------------------------------------


def test_traefik_routes_the_app_without_a_host_port(tmp_path: Path) -> None:
    _, template, root = generate_docker(
        tmp_path, traefik=True, traefik_domain="home.lab", traefik_entrypoint="websecure"
    )
    data = compose(root)
    app = data["services"]["app"]
    assert "ports" not in app
    assert app["networks"] == ["default", "traefik"]
    assert "traefik.http.routers.demo-app.rule=Host(`demo-app.home.lab`)" in app["labels"]
    assert "traefik.http.routers.demo-app.entrypoints=websecure" in app["labels"]
    assert "traefik.http.services.demo-app.loadbalancer.server.port=8000" in app["labels"]
    assert "traefik.docker.network=traefik" in app["labels"]
    assert data["networks"] == {"traefik": {"name": "traefik", "external": True}}
    assert not any(".tls" in label for label in app["labels"])
    assert any("docker network create traefik" in notice for notice in template.notices)
    assert "badge/Traefik-24A1C1" in read(root, "README.md")


def test_traefik_tls_labels_with_cert_resolver(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, traefik=True, traefik_cert_resolver="letsencrypt")
    labels = compose(root)["services"]["app"]["labels"]
    assert "traefik.http.routers.demo-app.tls=true" in labels
    assert "traefik.http.routers.demo-app.tls.certresolver=letsencrypt" in labels


def test_traefik_also_routes_the_web_uis(tmp_path: Path) -> None:
    _, _, root = generate_docker(
        tmp_path, db="postgres", with_pgadmin=True, with_minio=True, with_mail=True, traefik=True
    )
    services = compose(root)["services"]
    pgadmin_labels = services["pgadmin"]["labels"]
    assert "traefik.http.routers.demo-app-pgadmin.rule=Host(`pgadmin.demo-app.localhost`)" in (
        pgadmin_labels
    )
    assert any("minio.demo-app.localhost" in label for label in services["minio"]["labels"])
    assert any("server.port=9001" in label for label in services["minio"]["labels"])
    assert any("mail.demo-app.localhost" in label for label in services["mailpit"]["labels"])
    assert "labels" not in services["db"]


def test_traefik_django_hosts_use_dashes_not_underscores(tmp_path: Path) -> None:
    spec = make_spec(tmp_path, template="django", features=["docker"], docker=True, traefik=True)
    spec.name = "my_shop"
    from kickoff.features import apply_features

    template = apply_features(get_template("django"), spec)
    host = "my-shop.localhost"
    assert host in template.env_vars["DJANGO_ALLOWED_HOSTS"]
    assert template.env_vars["DJANGO_CSRF_TRUSTED_ORIGINS"] == f"http://{host},https://{host}"
    _, _, root = generate_docker(tmp_path / "x", "django", traefik=True)
    settings = read(root, "src/demo_app/settings.py")
    assert 'SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")' in settings
    assert "CSRF_TRUSTED_ORIGINS" in settings
    assert "demo-app.localhost" in parse_env(root)["DJANGO_ALLOWED_HOSTS"]
    _, _, plain = generate_docker(tmp_path / "y", "django")
    assert "SECURE_PROXY_SSL_HEADER" not in read(plain, "src/demo_app/settings.py")


def test_every_docker_file_is_valid_yaml_with_all_options(tmp_path: Path) -> None:
    _, _, root = generate_docker(
        tmp_path,
        "django",
        db="postgis",
        expose_db=True,
        with_pgadmin=True,
        with_redis=True,
        with_minio=True,
        with_mail=True,
        traefik=True,
        traefik_cert_resolver="le",
    )
    for name in ("docker-compose.yml", "compose.override.yml"):
        yaml.safe_load(read(root, name))
    assert "{" not in read(root, "Dockerfile").replace("${PYTHON_VERSION}", "")


# --- manifest -----------------------------------------------------------------


def test_manifest_round_trip_without_secrets(tmp_path: Path) -> None:
    spec, _, root = generate_docker(
        tmp_path, "django", db="postgres", with_redis=True, server="gunicorn", db_password="hunter2"
    )
    text = read(root, MANIFEST_NAME)
    assert "hunter2" not in text
    assert text == render_manifest(spec)
    loaded = read_manifest(root)
    assert loaded.name == "demo-app"
    assert loaded.template == "django"
    assert loaded.server == "gunicorn"
    assert loaded.db == "postgres"
    assert loaded.with_redis is True
    assert loaded.docker is True
    assert loaded.features == ["docker"]
    assert loaded.db_password is None


def test_manifest_missing_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="kickoff 0.4"):
        read_manifest(tmp_path)


# --- kickoff add --------------------------------------------------------------


def test_add_redis_to_a_docker_project(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, db="postgres")
    plan = build_plan(root, "redis")
    assert plan.dependencies == ["redis"]
    assert "REDIS_URL" in plan.env_added
    assert "docker-compose.yml" in plan.overwrite  # unmodified generated file: safe to replace
    assert plan.conflicts == {}
    write_plan(root, plan)
    write_manifest(root, plan)
    assert "redis" in compose(root)["services"]
    assert parse_env(root)["REDIS_URL"] == "redis://localhost:6379/0"
    assert parse_env(root, ".env.example")["REDIS_URL"] == "redis://localhost:6379/0"
    assert read_manifest(root).with_redis is True
    with pytest.raises(ValidationError, match="already"):
        build_plan(root, "redis")


def test_add_leaves_files_alone_when_the_feature_does_not_change_them(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path)
    (root / "Dockerfile").write_text("FROM scratch\n# my own\n", encoding="utf-8")
    plan = build_plan(root, "mail")
    assert "docker-compose.yml" in plan.overwrite
    for bucket in (plan.create, plan.overwrite, plan.conflicts):
        assert "Dockerfile" not in bucket
    write_plan(root, plan)
    assert read(root, "Dockerfile") == "FROM scratch\n# my own\n"


def test_add_conflicting_file_goes_next_to_the_original(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path)
    edited = read(root, "docker-compose.yml") + "# my change\n"
    (root / "docker-compose.yml").write_text(edited, encoding="utf-8")
    plan = build_plan(root, "redis")
    assert "docker-compose.yml" in plan.conflicts
    write_plan(root, plan)
    assert read(root, "docker-compose.yml") == edited
    assert "redis" in yaml.safe_load(read(root, "docker-compose.yml" + SUFFIX))["services"]


def test_add_prefect_creates_files_and_dependency(tmp_path: Path) -> None:
    _, _, root = generate_template(tmp_path, "default")
    plan = build_plan(root, "prefect")
    assert "prefect.yaml" in plan.create
    assert "src/demo_app/flows/hello.py" in plan.create
    assert plan.dependencies == ["prefect"]
    assert "src/{package}/flows" in plan.directories
    assert any("badge/Prefect" in badge for badge in plan.badges)
    write_plan(root, plan)
    assert (root / "prefect.yaml").is_file()


def test_add_dbt_aligns_with_the_existing_database_password(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, db="postgres", db_password="s3cret")
    plan = build_plan(root, "dbt", dbt_adapter="postgres")
    assert plan.new_spec.dbt_adapter == "postgres"
    assert plan.env_added["DBT_POSTGRES_PASSWORD"] == "s3cret"
    assert plan.env_example_added["DBT_POSTGRES_PASSWORD"] == "change-me"
    assert plan.dependencies == ["dbt-postgres"]
    assert "dbt/dbt_project.yml" in plan.create
    assert "dbt/target/" in plan.gitignore_lines


def test_add_traefik_reports_changed_allowed_hosts(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path, "django")
    plan = build_plan(root, "traefik", traefik_domain="home.lab")
    assert "demo-app.home.lab" in plan.env_changed["DJANGO_ALLOWED_HOSTS"]
    assert "DJANGO_CSRF_TRUSTED_ORIGINS" in plan.env_added
    assert "src/demo_app/settings.py" in plan.overwrite  # proxy header + CSRF origins


def test_add_rejects_bad_requests(tmp_path: Path) -> None:
    _, _, root = generate_docker(tmp_path)
    with pytest.raises(ValidationError, match="Unknown feature"):
        build_plan(root, "kafka")
    with pytest.raises(ValidationError, match="needs a database"):
        build_plan(root, "pgadmin")
    with pytest.raises(ValidationError, match="Unknown dbt adapter"):
        build_plan(root, "dbt", dbt_adapter="oracle")
    with pytest.raises(ValidationError, match="already"):
        build_plan(root, "docker")


def test_add_docker_to_a_plain_project(tmp_path: Path) -> None:
    _, _, root = generate_template(tmp_path, "default")
    plan = build_plan(root, "docker")
    assert {"Dockerfile", "docker-compose.yml", ".dockerignore"} <= set(plan.create)
    assert plan.new_spec.docker
    write_plan(root, plan)
    write_manifest(root, plan)
    assert "docker" in read_manifest(root).features


# --- custom templates ---------------------------------------------------------


def write_custom(directory: Path, name: str, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.toml").write_text(body, encoding="utf-8")


def test_custom_template_extends_a_builtin(tmp_path: Path) -> None:
    write_custom(
        tmp_path,
        "api",
        '''
extends = "django"
description = "Django with an API layer"
dependencies = ["httpx"]
dev_dependencies = ["hypothesis"]
ci_jobs = ["notebooks"]
badges = ["redis"]
stack_notes = ["Internal API"]

[directories]
"src/{package}/api" = "HTTP API"

[commands]
"Run API" = "uv run uvicorn x:y"

[env_vars]
API_KEY = "change-me"

[ruff_per_file_ignores]
"scripts/**" = ["T201"]

[files]
"src/__PACKAGE__/api/__init__.py" = "\\"\\"\\"API of __NAME__.\\"\\"\\"\\n"
''',
    )
    templates, paths, errors = load_custom_templates(tmp_path)
    assert errors == {}
    template = templates["api"]
    assert template.name == "api"
    assert template.description == "Django with an API layer"
    assert template.dependencies == ["django", "typer", "httpx"]
    assert template.dev_dependencies[-1] == "hypothesis"
    assert template.directories["src/{package}/api"] == "HTTP API"
    assert "src/core" in template.directories  # inherited
    assert template.commands["Run API"] == "uv run uvicorn x:y"
    assert "Migrate" in template.commands
    assert template.env_vars["API_KEY"] == "change-me"
    assert "DJANGO_DEBUG" in template.env_vars
    assert template.ruff_per_file_ignores["scripts/**"] == ["T201"]
    assert template.ruff_per_file_ignores["**/migrations/*.py"] == ["N999"]
    assert paths["api"] == tmp_path / "api.toml"
    files = template.render_files(make_spec(tmp_path / "p", template="api"))
    assert files["src/demo_app/api/__init__.py"] == '"""API of demo-app."""\n'
    assert "manage.py" in files  # the base template's files are still generated


def test_custom_template_generates_a_project(tmp_path: Path) -> None:
    write_custom(
        tmp_path / "cfg",
        "mine",
        'description = "Mine"\ndependencies = ["rich"]\n[files]\n"NOTES.md" = "# __NAME__\\n"\n',
    )
    from kickoff.generators.files import write_base_files
    from kickoff.generators.structure import create_directories

    template = get_template("mine", tmp_path / "cfg")
    spec = make_spec(tmp_path / "out", template="mine")
    create_directories(spec, template)
    write_base_files(spec, template)
    assert read(spec.target_dir, "NOTES.md") == "# demo-app\n"
    assert read_manifest(spec.target_dir).template == "mine"
    assert "rich" in template.dependencies


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ('colour = "red"', "unknown key"),
        ('dependencies = "httpx"', "list of strings"),
        ("directories = []", "must be a table"),
        ("[commands]\nx = 1", "must be a string"),
        ('extends = "nope"', "built-in template"),
        ('ci_jobs = ["deploy"]', "unknown ci_jobs"),
        ('badges = ["myspace"]', "unknown badges"),
        ('description = 5', "must be a string"),
    ],
)
def test_invalid_custom_templates_are_reported(tmp_path: Path, body: str, message: str) -> None:
    write_custom(tmp_path, "broken", body)
    templates, _, errors = load_custom_templates(tmp_path)
    assert templates == {}
    assert message in errors["broken.toml"]


def test_custom_template_name_rules(tmp_path: Path) -> None:
    write_custom(tmp_path, "django", 'description = "x"')
    write_custom(tmp_path, "Bad_Name", 'description = "x"')
    write_custom(tmp_path, "notoml", "this is = = not toml")
    templates, _, errors = load_custom_templates(tmp_path)
    assert templates == {}
    assert "built-in" in errors["django.toml"]
    assert "file name must match" in errors["Bad_Name.toml"]
    assert "notoml.toml" in errors


def test_registry_merges_builtin_and_custom(tmp_path: Path) -> None:
    write_custom(tmp_path, "mine", 'description = "Mine"')
    write_custom(tmp_path, "broken", "colour = 1")
    entries, errors = all_templates(tmp_path)
    assert {"default", "django", "jupyter", "mine"} <= set(entries)
    assert entries["mine"].source.endswith("mine.toml")
    assert entries["default"].source == "built-in"
    assert "broken.toml" in errors
    with pytest.raises(ValidationError, match="invalid"):
        get_template("broken", tmp_path)
    with pytest.raises(ValidationError, match="Unknown template"):
        get_template("nope", tmp_path)


def test_build_template_requires_valid_data() -> None:
    with pytest.raises(CustomTemplateError):
        build_template("x", {"nope": 1})
