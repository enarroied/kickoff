"""File contents for the Django template.

The files are plain Python strings (no Jinja). ``__PACKAGE__`` and ``__NAME__``
are replaced with the project's package and project names.
"""

from __future__ import annotations

from kickoff.models import ProjectSpec

SQLITE_DATABASES = """\
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}"""

# PostgreSQL is used when POSTGRES_DB is set (.env, docker compose, CI); otherwise SQLite, so
# `pytest` works on a machine where the database container is not reachable.
POSTGRES_DATABASES = SQLITE_DATABASES + """

if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        },
    }"""

# PostGIS has no SQLite fallback: django.contrib.gis needs the spatial database (and GDAL).
POSTGIS_DATABASES = """\
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    },
}"""

# Behind Traefik the original scheme arrives in X-Forwarded-Proto.
PROXY_BLOCK = """\
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

"""

# Mailpit (`--with-mail`) catches every outgoing mail; its web UI shows them.
EMAIL_BLOCK = """\
EMAIL_HOST = os.environ.get("MAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("MAIL_PORT", "1025"))

"""

DATABASE_BLOCKS = {
    "none": SQLITE_DATABASES,
    "postgres": POSTGRES_DATABASES,
    "postgis": POSTGIS_DATABASES,
}

MANAGE_PY = '''\
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
from pathlib import Path

from django.core.management import execute_from_command_line


def main() -> None:
    """Run administrative tasks."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__PACKAGE__.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
'''

SETTINGS_PY = '''\
"""Django settings for __NAME__.

Values that change between environments are read from environment variables:
DJANGO_SECRET_KEY, DJANGO_DEBUG ("1" or "0") and DJANGO_ALLOWED_HOSTS (comma separated),
plus the POSTGRES_* variables when the project was created with a database.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-development-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host
]

CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin
]

__PROXY__
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
__GIS_APP__
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "__PACKAGE__.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "__PACKAGE__.wsgi.application"
ASGI_APPLICATION = "__PACKAGE__.asgi.application"

__DATABASES__

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

__EMAIL__
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
'''

URLS_PY = '''\
"""URL configuration for __NAME__."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
'''

ASGI_PY = '''\
"""ASGI entry point for __NAME__."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__PACKAGE__.settings")

application = get_asgi_application()
'''

WSGI_PY = '''\
"""WSGI entry point for __NAME__."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "__PACKAGE__.settings")

application = get_wsgi_application()
'''

CORE_APPS_PY = '''\
"""Core app configuration."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
'''

CORE_VIEWS_PY = '''\
"""Views for the core app."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Render the landing page."""
    return render(request, "home.html")
'''

CORE_URLS_PY = '''\
"""URL routes for the core app."""

from django.urls import path

from core import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
]
'''

HOME_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>__NAME__</title>
  </head>
  <body>
    <h1>__NAME__</h1>
    <p>Your Django project is running.</p>
  </body>
</html>
"""

CORE_TESTS_PY = '''\
"""Tests for the core app."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_home_page_renders(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
'''


def django_files(spec: ProjectSpec) -> dict[str, str]:
    """Return the Django skeleton as {relative path: content}."""
    package = spec.package_name
    settings = (
        SETTINGS_PY.replace("__DATABASES__", DATABASE_BLOCKS[spec.db])
        .replace("__GIS_APP__\n", '    "django.contrib.gis",\n' if spec.db == "postgis" else "")
        .replace("__PROXY__\n", PROXY_BLOCK if spec.traefik else "")
        .replace("__EMAIL__\n", EMAIL_BLOCK if spec.with_mail else "")
    )
    files = {
        "manage.py": MANAGE_PY,
        f"src/{package}/settings.py": settings,
        f"src/{package}/urls.py": URLS_PY,
        f"src/{package}/asgi.py": ASGI_PY,
        f"src/{package}/wsgi.py": WSGI_PY,
        "src/core/__init__.py": '"""Core Django app."""\n',
        "src/core/apps.py": CORE_APPS_PY,
        "src/core/models.py": '"""Models for the core app."""\n',
        "src/core/admin.py": '"""Admin registrations for the core app."""\n',
        "src/core/views.py": CORE_VIEWS_PY,
        "src/core/urls.py": CORE_URLS_PY,
        "src/core/migrations/__init__.py": "",
        "templates/home.html": HOME_HTML,
        "tests/test_core.py": CORE_TESTS_PY,
    }
    return {
        path: content.replace("__PACKAGE__", package).replace("__NAME__", spec.name)
        for path, content in files.items()
    }
