# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Generating config files via the CLI."""

import logging

import click


from .common import common
from ..gp import GPParameters
from ..gids import GidsAppletParameters


_LOG = logging.getLogger(__name__)


@common.command()
@click.argument(
    "toml_filename",
    type=click.Path(file_okay=True, dir_okay=False, writable=True),
)
def gids_init(toml_filename):
    """Generate GidsApplet card init parameters into a TOML file"""
    params = GidsAppletParameters.generate()
    _LOG.info("Writing %s", toml_filename)
    params.write_toml(toml_filename)


@common.command()
@click.argument(
    "toml_filename",
    type=click.Path(file_okay=True, dir_okay=False, writable=True),
)
def gp(toml_filename):
    """Generate GlobalPlatform card parameters into a TOML file"""
    params = GPParameters.generate()
    _LOG.info("Writing %s", toml_filename)
    params.write_toml(toml_filename)


if __name__ == "__main__":
    common()
