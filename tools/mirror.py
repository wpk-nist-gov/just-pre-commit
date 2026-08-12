# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "packaging>=26.3",
#   "urllib3>=2.7.0",
# ]
# ///
"""Update just-pre-commit to the latest version of just."""

# ruff:file-ignore[undocumented-public-function]
import logging
import re
import shlex
import subprocess
from argparse import ArgumentParser
from collections.abc import Iterable, Sequence
from functools import partial
from pathlib import Path
from typing import Any

import tomllib
import urllib3
from packaging.requirements import Requirement
from packaging.version import Version

PACKAGE = "rust-just"


FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("mirror")


def main() -> int:
    parser = ArgumentParser()
    _ = parser.add_argument(
        "--pull-request",
        action="store_true",
        help="""
        Create single pull request. Useful for use in ci.
        """,
    )
    _ = parser.add_argument(
        "--max-version",
        type=Version,
        default="10000000000.0.0",
        help="Maximum allowed version",
    )
    _ = parser.add_argument(
        "--dry-run",
        action="store_true",
        help="""
        Do not commit or create pull request. Note that files will still be
        changed.
        """,
    )

    opts = parser.parse_args()
    pull_request: bool = opts.pull_request
    max_version: Version = opts.max_version
    dry_run: bool = opts.dry_run

    with Path(Path(__file__).parent.parent / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)

    all_versions = get_all_versions()
    current_version = get_current_version(pyproject=pyproject)
    target_versions = [v for v in all_versions if current_version < v <= max_version]

    logger.info("all_version: %s", all_versions)
    logger.info("current_version: %s", current_version)
    logger.info("target_versions: %s", target_versions)
    logger.info("pull_request: %s", pull_request)

    for version in target_versions:
        paths = process_version(version)
        if subprocess.check_output(["git", "status", "-s"]).strip():
            # update lock files (allow errors)
            _ = subprocess.run(["uv", "lock"], check=False)

            if pull_request:
                create_pull_request(version, *paths, "uv.lock", dry_run=dry_run)
                # only allow one pull-request at a time:
                return 0

            create_commit(version, *paths, "uv.lock", dry_run=dry_run)
        else:
            logger.info("No change v%s", version)

    return 0


def create_pull_request(version: Version, *paths: str, dry_run: bool) -> None:
    check_call = partial(maybe_check_call, dry_run=dry_run)
    # new branch
    branch = f"release/v{version}"
    _ = check_call(["git", "checkout", "-b", branch])
    _ = check_call(["git", "add", *paths])
    _ = check_call(
        ["git", "commit", "-m", f"chore: Mirror {version}"],
    )
    # push
    _ = check_call([
        "git",
        "push",
        "origin",
        f"HEAD:{branch}",
    ])
    # create pull request
    _ = check_call(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            branch,
            "-t",
            f"chore: Mirror {version}",
            "-b",
            f"Autorelease version {version}",
        ],
    )
    # enable automerge
    _ = check_call(["gh", "pr", "merge", "-s", "--auto", branch])


def create_commit(version: Version, *paths: str, dry_run: bool) -> None:
    check_call = partial(maybe_check_call, dry_run=dry_run)
    # new commit
    _ = check_call(["git", "add", *paths])
    # update lock files (allow errors)
    _ = check_call(["uv", "lock"])

    _ = check_call(["git", "commit", "-m", f"chore: Mirror {version}"])
    _ = check_call(["git", "tag", f"v{version}"])


def maybe_check_call(args: Sequence[str], dry_run: bool = False, **kwargs: Any) -> int:
    logger.info("Run: %s", shlex.join(args))
    if dry_run:
        return 0
    return subprocess.check_call(args, **kwargs)


def get_all_versions() -> list[Version]:
    response = urllib3.request("GET", f"https://pypi.org/pypi/{PACKAGE}/json")
    if response.status != 200:  # ruff:ignore[magic-value-comparison]
        msg = "Failed to fetch versions from pypi"
        raise RuntimeError(msg)

    versions = [Version(release) for release in response.json()["releases"]]
    return sorted(versions)


def get_current_version(pyproject: dict[str, Any]) -> Version:
    # check that package in dependencies and has the correct form
    requirements = [Requirement(d) for d in pyproject["project"]["dependencies"]]
    if (
        requirement := next((r for r in requirements if r.name == PACKAGE), None)
    ) is None:
        msg = f"pyproject.toml does not have {PACKAGE} requirement"
        raise RuntimeError(msg)

    specifiers = list(requirement.specifier)

    if len(specifiers) != 1 or specifiers[0].operator != "==":
        msg = f"{PACKAGE}'s specifier should be exact matching, but `{requirement}`"
        raise RuntimeError(msg)

    # get version from project.version
    return Version(pyproject["project"]["version"])


def process_version(version: Version) -> Iterable[str]:
    def replace_readme_md(content: str) -> str:
        return re.sub(r"rev: v\d+\.\d+\.\d+", f"rev: v{version}", content)

    def replace_pyproject_toml(content: str) -> str:
        # replace package=={version}
        contents = re.sub(rf'"{PACKAGE}==.*"', rf'"{PACKAGE}=={version}"', content)
        # replace version="{version}"
        return re.sub(
            r'^(version\s*=\s*)"(\d+\.\d+\.\d+)"\s*$',
            rf'\g<1>"{version}"',
            contents,
            flags=re.MULTILINE,
        )

    paths = {
        "README.md": replace_readme_md,
        "pyproject.toml": replace_pyproject_toml,
    }

    for path, replacer in paths.items():
        p = Path(path)
        content = replacer(p.read_text(encoding="utf-8"))
        _ = p.write_text(content, encoding="utf-8")

    return paths.keys()


if __name__ == "__main__":
    raise SystemExit(main())
