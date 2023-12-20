# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
"""Generating config files via the CLI."""

import logging

import click

import yaml


from .common import common
from ..gp import GPParameters
from ..gids import GidsAppletParameters


_LOG = logging.getLogger(__name__)


@common.command()
@click.argument(
    "yaml_filename",
    type=click.Path(file_okay=True, dir_okay=False, writable=True),
)
def gids_init(yaml_filename):
    """Generate GidsApplet card init parameters into a YAML file"""
    params = GidsAppletParameters.generate()
    _LOG.info("Writing %s", yaml_filename)
    with open(yaml_filename, "w", encoding="utf-8") as fp:
        yaml.dump(params, fp)


@common.command()
@click.argument(
    "yaml_filename",
    type=click.Path(file_okay=True, dir_okay=False, writable=True),
)
def gp(yaml_filename):
    """Generate GlobalPlatform card parameters into a YAML file"""
    params = GPParameters.generate()
    _LOG.info("Writing %s", yaml_filename)
    with open(yaml_filename, "w", encoding="utf-8") as fp:
        yaml.dump(params, fp)
        # fp.write(YAMLWizard.to_yaml(params))


if __name__ == "__main__":
    common()
