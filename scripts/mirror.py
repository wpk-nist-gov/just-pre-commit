# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "packaging==23.1",
#   "urllib3==2.0.5",
# ]
# ///
"""Update just-pre-commit to the latest version of just."""

# ruff: noqa: T201

import re
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tomllib
import urllib3
from packaging.requirements import Requirement
from packaging.version import Version

PACKAGE = "rust-just"


def main() -> int:
    with Path(Path(__file__).parent.parent / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    all_versions = get_all_versions()
    current_version = get_current_version(pyproject=pyproject)
    target_versions = [v for v in all_versions if v > current_version]

    print(f"{all_versions=}")
    print(f"{current_version=}")
    print(f"{target_versions=}")

    for version in target_versions:
        paths = process_version(version)
        if subprocess.check_output(["git", "status", "-s"]).strip():
            _ = subprocess.run(["git", "add", *paths], check=True)
            _ = subprocess.run(
                ["git", "commit", "-m", f"Mirror: {version}"], check=True
            )
            _ = subprocess.run(["git", "tag", f"v{version}"], check=True)
        else:
            print(f"No change v{version}")

    return 0


def get_all_versions() -> list[Version]:
    response = urllib3.request("GET", f"https://pypi.org/pypi/{PACKAGE}/json")
    if response.status != 200:  # noqa: PLR2004
        msg = "Failed to fetch versions from pypi"
        raise RuntimeError(msg)

    versions = [Version(release) for release in response.json()["releases"]]
    return sorted(versions)


def get_current_version(pyproject: dict[str, Any]) -> Version:
    requirements = [Requirement(d) for d in pyproject["project"]["dependencies"]]
    requirement = next((r for r in requirements if r.name == PACKAGE), None)
    if requirement is None:
        msg = f"pyproject.toml does not have {PACKAGE} requirement"
        raise RuntimeError(msg)

    specifiers = list(requirement.specifier)

    if len(specifiers) != 1 or specifiers[0].operator != "==":
        msg = f"{PACKAGE}'s specifier should be exact matching, but `{requirement}`"
        raise RuntimeError(msg)

    return Version(specifiers[0].version)


def process_version(version: Version) -> Iterable[str]:
    def replace_pyproject_toml(content: str) -> str:
        return re.sub(rf'"{PACKAGE}==.*"', rf'"{PACKAGE}=={version}"', content)

    def replace_readme_md(content: str) -> str:
        return re.sub(r"rev: v\d+\.\d+\.\d+", f"rev: v{version}", content)
        # return re.sub(r"/ruff/\d+\.\d+\.\d+\.svg", f"/ruff/{version}.svg", content)  # noqa: ERA001

    paths = {
        "pyproject.toml": replace_pyproject_toml,
        "README.md": replace_readme_md,
    }

    for path, replacer in paths.items():
        p = Path(path)
        content = replacer(p.read_text(encoding="utf-8"))
        _ = p.write_text(content, encoding="utf-8")

    return paths.keys()


if __name__ == "__main__":
    raise SystemExit(main())
