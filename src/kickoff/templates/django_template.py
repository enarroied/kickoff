"""The 'django' template — Django web applications (ASGI)."""

from __future__ import annotations

from dataclasses import replace

from kickoff import defaults
from kickoff.models import DockerConfig, ServerSpec
from kickoff.templates.default_template import DEFAULT_TEMPLATE
from kickoff.templates.django_files import django_files

# Built on top of the default template: only the differences are listed here.
DJANGO_TEMPLATE = replace(
    DEFAULT_TEMPLATE,
    name="django",
    description="Django web application (ASGI, uvicorn)",
    directories={
        "src/{package}": "Django project (settings, urls, ASGI)",
        "src/core": "core Django app",
        "templates": "project-level HTML templates",
        "static": "static source files",
        "media": "user uploads (gitignored)",
        "tests": "tests",
        "docs": "documentation",
        "img": "images and diagrams",
        "scripts": "utility scripts",
        "data": "local data (gitignored)",
        "data/raw": "",
        "data/interim": "",
        "data/processed": "",
    },
    dependencies=["django", "typer"],
    dev_dependencies=[
        *DEFAULT_TEMPLATE.dev_dependencies,
        "pytest-django",
        "django-stubs",
        "django-stubs-ext",
        "factory-boy",
    ],
    ruff_select_extra=["DJ"],
    ruff_per_file_ignores={"**/migrations/*.py": ["N999"]},
    ruff_extra={"isort": {"known-first-party": ["{package}", "core"]}},
    pytest_options={"DJANGO_SETTINGS_MODULE": "{package}.settings"},
    ci_jobs=[*DEFAULT_TEMPLATE.ci_jobs, "django-check", "django-migrations"],
    ignored_directories=["data", "media"],
    gitignore_extra=["db.sqlite3", "staticfiles/"],
    stack_notes=[
        "Django (ASGI), run with {server}",
        "Settings read DJANGO_SECRET_KEY, DJANGO_DEBUG, DJANGO_ALLOWED_HOSTS from the environment",
    ],
    env_vars={
        "DJANGO_SECRET_KEY": defaults.ENV_SECRET,
        "DJANGO_DEBUG": "1",
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
    },
    badges=["django"],
    db_aware=True,
    testing_notes=[
        "Django tests use pytest-django: the `client` fixture, and `@pytest.mark.django_db` "
        "for tests that touch the database"
    ],
    docker_config=DockerConfig(
        container_port=8000,
        healthcheck_path="/",
        entrypoint_steps=[
            "python manage.py migrate --noinput",
            "python manage.py collectstatic --noinput",
        ],
    ),
    # `uv run --env-file .env` loads the settings; CI and pytest use the built-in defaults.
    commands={
        "Migrate": "uv run --env-file .env python manage.py migrate",
        "Make migrations": "uv run --env-file .env python manage.py makemigrations",
        "Create superuser": "uv run --env-file .env python manage.py createsuperuser",
        "Django check": "uv run --env-file .env python manage.py check",
    },
    servers={
        "uvicorn": ServerSpec(
            dependencies=["uvicorn"],
            command=(
                "uv run --env-file .env uvicorn {package}.asgi:application "
                "--app-dir src --reload"
            ),
            docker_command=[
                "uvicorn",
                "{package}.asgi:application",
                "--app-dir",
                "src",
                "--host",
                "0.0.0.0",
                "--port",
                "{port}",
            ],
            docker_dev_command=[
                "uvicorn",
                "{package}.asgi:application",
                "--app-dir",
                "src",
                "--host",
                "0.0.0.0",
                "--port",
                "{port}",
                "--reload",
            ],
        ),
        "gunicorn": ServerSpec(
            dependencies=["gunicorn"],
            command="uv run --env-file .env gunicorn {package}.wsgi:application --chdir src",
            docker_command=[
                "gunicorn",
                "{package}.wsgi:application",
                "--chdir",
                "src",
                "--bind",
                "0.0.0.0:{port}",
            ],
            docker_dev_command=[
                "gunicorn",
                "{package}.wsgi:application",
                "--chdir",
                "src",
                "--bind",
                "0.0.0.0:{port}",
                "--reload",
            ],
        ),
    },
    render_files=django_files,
)
