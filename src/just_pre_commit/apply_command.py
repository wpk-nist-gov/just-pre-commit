"""Apply command that works on single file to multiple files."""

from __future__ import annotations

import logging
import shlex
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


FORMAT = "[%(name)s - %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger("apply-command")


def _apply_command(command: str, extras: Sequence[str], path: str) -> int:
    cmd = (command, *extras, str(path))
    logger.info("%s", shlex.join(cmd))
    code = subprocess.call(cmd)
    logger.info("return code: %s", code)
    return code


def _get_options(argv: Sequence[str] | None = None) -> tuple[str, list[str], list[str]]:
    from argparse import ArgumentParser

    parser = ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "command",
        help="""
        Command to run. Extra arguments to ``command`` will be parsed as well.
        Note that ``command`` will be parsed with ``shlex.split``. So, if you
        need to pass complex arguments, you should wrap ``command`` and these
        arguments in a single string. For example, to run ``command --option
        a`` over ``file1`` and ``file2``, you should use ``apply-command
        "command --option a" file1 file2``
        """,
    )
    _ = parser.add_argument(
        dest="paths",
        nargs="+",
        help="Files to apply ``command`` to.",
    )

    options, extras = parser.parse_known_args(argv)

    paths: list[str] = options.paths
    command, *command_extras = shlex.split(options.command)

    # NOTE(wpk): put command extras last for special case of just --fmt --unstable --justfile
    # so `--justfile` will remain last
    return command, [*extras, *command_extras], paths


def main(argv: Sequence[str] | None = None) -> int:
    """Main functionality"""
    command, extras, paths = _get_options(argv)

    return_code = 0
    for path in paths:
        return_code += _apply_command(command, extras, path)
    return return_code
