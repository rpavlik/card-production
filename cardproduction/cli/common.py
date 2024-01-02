# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Common utilities for command line modules."""

import logging
from dataclasses import dataclass
from typing import Optional

import click
from dataclasses_json import LetterCase, dataclass_json

from ..gp import GPParameters

_LOG = logging.getLogger(__name__)


@click.group()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    show_default=True,
    default=False,
    help="Verbose logging",
)
@click.pass_context
def common(ctx, verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@dataclass_json(letter_case=LetterCase.SNAKE)  # type: ignore
@dataclass
class GPConfig:
    """Parameters for setting up GP."""

    current_parameters_filename: Optional[str] = None
    desired_parameters_filename: Optional[str] = None


def load_or_generate_gp_params(filename) -> GPParameters:
    """Load a GP parameters file, if one exists, or generate one."""
    log = _LOG.getChild("load_or_generate_gp_params")
    loaded = None
    try:
        log.info(
            "Attempting to load GP parameters from %s",
            filename,
        )
        loaded = GPParameters.load_toml(filename)
    except FileNotFoundError:
        pass
    if loaded:
        return loaded

    log.info(
        "Generating random GP parameters and saving to %s",
        filename,
    )
    ret = GPParameters.generate()
    ret.write_toml(filename)
    return ret
