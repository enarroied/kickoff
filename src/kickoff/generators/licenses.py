"""Write the LICENSE file."""

from __future__ import annotations

from datetime import UTC, datetime
from importlib import resources

from kickoff.models import ProjectSpec
from kickoff.utils import logging

MIT_TEXT = """\
MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Licenses whose full text ships with kickoff (src/kickoff/assets/licenses/).
BUNDLED_LICENSES = {"Apache-2.0": "Apache-2.0.txt", "GPL-3.0": "GPL-3.0.txt"}


def render_license(spec: ProjectSpec) -> str | None:
    """Return the LICENSE text, or None when no license was requested."""
    if spec.license == "none":
        return None
    if spec.license == "MIT":
        holder = spec.author_name or f"{spec.name} contributors"
        return MIT_TEXT.format(year=datetime.now(tz=UTC).year, holder=holder)
    bundled = resources.files("kickoff") / "assets" / "licenses" / BUNDLED_LICENSES[spec.license]
    return bundled.read_text(encoding="utf-8")


def write_license(spec: ProjectSpec) -> None:
    text = render_license(spec)
    if text is None:
        return
    logging.step("Writing LICENSE")
    (spec.target_dir / "LICENSE").write_text(text, encoding="utf-8")
    logging.success(f"LICENSE written ({spec.license})")
