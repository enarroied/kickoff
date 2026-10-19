"""CLI tests using Typer's runner."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from kickoff import __version__
from kickoff.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_templates_lists_every_template() -> None:
    result = runner.invoke(app, ["templates"])
    assert result.exit_code == 0
    for name in ("default", "django", "jupyter"):
        assert name in result.output


@pytest.mark.parametrize("bad_name", ["1project", "-project", "my project"])
def test_invalid_project_name_is_rejected(bad_name: str, tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", bad_name, "--path", str(tmp_path), "--yes"])
    assert result.exit_code == 1


@pytest.mark.parametrize(
    "bad_option",
    [["--python", "2.7"], ["--server", "waitress"], ["--license", "WTFPL"], ["--template", "nope"]],
)
def test_invalid_option_values_are_rejected(bad_option: list[str], tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "demo", *bad_option, "--path", str(tmp_path), "-y"])
    assert result.exit_code == 1


@pytest.mark.parametrize(
    "args",
    [["--dbt-adapter", "duckdb"], ["--with-dbt", "--dbt-adapter", "oracle"]],
)
def test_invalid_dbt_adapter_usage_is_rejected(args: list[str], tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "demo", *args, "--path", str(tmp_path), "-y"])
    assert result.exit_code == 1


def test_dry_run_with_features_creates_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("kickoff.commands.new.command_exists", lambda _name: True)
    args = ["new", "demo", "--with-prefect", "--with-dbt", "--dbt-adapter", "postgres"]
    result = runner.invoke(app, [*args, "--path", str(tmp_path), "--dry-run", "--yes"])
    assert result.exit_code == 0
    assert "dbt adapter: postgres" in result.output
    assert not (tmp_path / "demo").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--db-password", "x"],
        ["--expose-db"],
        ["--with-pgadmin"],
        ["--db", "postgres", "--db-port", "5433"],
        ["--db", "postgres", "--expose-db", "--db-port", "0"],
        ["--app-port", "70000"],
    ],
)
def test_inconsistent_database_options_are_rejected(args: list[str], tmp_path: Path) -> None:
    result = runner.invoke(app, ["new", "demo", *args, "--path", str(tmp_path), "-y"])
    assert result.exit_code == 1


def test_db_enables_docker_in_the_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("kickoff.commands.new.command_exists", lambda _name: True)
    args = ["new", "demo", "--db", "postgis", "--with-pgadmin", "--app-port", "8100"]
    result = runner.invoke(app, [*args, "--path", str(tmp_path), "--dry-run", "--yes"])
    assert result.exit_code == 0
    assert "enabling --docker" in result.output
    assert "postgis database" in result.output
    assert "pgAdmin" in result.output
    assert "port 8100" in result.output
    assert not (tmp_path / "demo").exists()


@pytest.mark.parametrize("template", ["default", "django", "jupyter"])
def test_dry_run_creates_nothing(
    template: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("kickoff.commands.new.command_exists", lambda _name: True)
    result = runner.invoke(
        app,
        ["new", "demo", "--template", template, "--path", str(tmp_path), "--dry-run", "--yes"],
    )
    assert result.exit_code == 0
    assert not (tmp_path / "demo").exists()


# --- v0.4 ---------------------------------------------------------------------


def test_service_flags_enable_docker_in_the_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("kickoff.commands.new.command_exists", lambda _name: True)
    args = ["new", "demo", "--with-redis", "--with-mail", "--traefik"]
    args += ["--traefik-domain", "lab.home"]
    result = runner.invoke(app, [*args, "--path", str(tmp_path), "--dry-run", "--yes"])
    assert result.exit_code == 0
    assert "enabling --docker" in result.output
    assert "redis" in result.output
    assert "demo.lab.home" in result.output
    assert not (tmp_path / "demo").exists()


def test_traefik_domain_requires_traefik(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["new", "demo", "--traefik-domain", "x.y", "--path", str(tmp_path), "-y"]
    )
    assert result.exit_code == 1


def test_add_needs_a_kickoff_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["add", "redis", "--path", str(tmp_path), "--yes"])
    assert result.exit_code == 1


def test_add_rejects_unknown_features(tmp_path: Path) -> None:
    result = runner.invoke(app, ["add", "kafka", "--path", str(tmp_path), "--yes"])
    assert result.exit_code == 1


@pytest.fixture
def config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return tmp_path / "xdg" / "kickoff"


def test_config_set_and_show(config_home: Path) -> None:
    result = runner.invoke(app, ["config", "set", "defaults.python_version", "3.13"])
    assert result.exit_code == 0
    text = (config_home / "config.toml").read_text(encoding="utf-8")
    assert text.startswith("# kickoff global configuration")
    assert 'python_version = "3.13"' in text
    shown = runner.invoke(app, ["config", "show"])
    assert '"python_version": "3.13"' in shown.output


def test_config_set_converts_types(config_home: Path) -> None:
    assert runner.invoke(app, ["config", "set", "docker.default_app_port", "9000"]).exit_code == 0
    assert runner.invoke(app, ["config", "set", "github.create_repo", "false"]).exit_code == 0
    text = (config_home / "config.toml").read_text(encoding="utf-8")
    assert "default_app_port = 9000" in text
    assert "create_repo = false" in text


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("defaults.python_version", "3.99"),
        ("defaults.license", "WTFPL"),
        ("defaults.template", "nope"),
        ("docker.default_app_port", "99999"),
        ("docker.default_app_port", "abc"),
        ("github.create_repo", "maybe"),
        ("defaults.nope", "x"),
    ],
)
def test_config_set_rejects_bad_input(config_home: Path, key: str, value: str) -> None:
    result = runner.invoke(app, ["config", "set", key, value])
    assert result.exit_code != 0
    assert not (config_home / "config.toml").exists()


def test_config_path(config_home: Path) -> None:
    result = runner.invoke(app, ["config", "path"])
    assert result.exit_code == 0
    assert "config.toml" in result.output


@pytest.mark.parametrize(
    ("content", "expected_exit"), [("[defaults]\nbranch = 'x'\n", 0), ("[[", 1)]
)
def test_config_edit_validates_the_result(
    config_home: Path, monkeypatch: pytest.MonkeyPatch, content: str, expected_exit: int
) -> None:
    def fake_edit(filename: str) -> None:
        Path(filename).write_text(content, encoding="utf-8")

    monkeypatch.setattr("kickoff.commands.config_cmd.click.edit", fake_edit)
    result = runner.invoke(app, ["config", "edit"])
    assert result.exit_code == expected_exit


def test_custom_templates_are_listed_and_usable(
    config_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    templates = config_home / "templates"
    templates.mkdir(parents=True)
    (templates / "mine.toml").write_text('description = "My template"\n', encoding="utf-8")
    (templates / "broken.toml").write_text("colour = 1\n", encoding="utf-8")
    listing = runner.invoke(app, ["templates"])
    assert "mine" in listing.output
    assert "ignored" in listing.output
    monkeypatch.setattr("kickoff.commands.new.command_exists", lambda _name: True)
    result = runner.invoke(
        app, ["new", "demo", "--template", "mine", "--path", str(tmp_path), "--dry-run", "-y"]
    )
    assert result.exit_code == 0
    args = ["new", "demo", "--template", "broken", "--path", str(tmp_path), "-y"]
    broken = runner.invoke(app, args)
    assert broken.exit_code == 1
