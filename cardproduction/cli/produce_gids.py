# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Set up a card with GidsApplet and a key/certificate."""

import logging
from dataclasses import dataclass, field
from typing import List, Optional
from dataclasses_json import LetterCase, dataclass_json

import click
import toml

from .common import GPConfig, load_or_generate_gp_params
from ..gids import GidsApplet, GidsAppletKeyLoading, GidsAppletParameters
from ..gp import GPParameters, GP


_LOG = logging.getLogger(__name__)


@dataclass_json(letter_case=LetterCase.SNAKE)  # type: ignore
@dataclass
class ProcedureConfig:
    """Configure a card production procedure for the Gids applet."""

    gids_parameters_filename: str
    install_and_init_gids: bool
    gp_config: GPConfig = field(default_factory=GPConfig)
    key_loading: List[GidsAppletKeyLoading] = field(default_factory=list)


def load_or_generate_gids_params(filename) -> GidsAppletParameters:
    """Load a GidsApplet parameters file, if one exists, or generate one."""
    log = _LOG.getChild("load_or_generate_gids_params")
    loaded = None
    try:
        log.info(
            "Attempting to load GidsApplet init parameters from %s",
            filename,
        )
        loaded = GidsAppletParameters.load_toml(filename)
    except FileNotFoundError:
        pass
    if loaded:
        return loaded

    log.info(
        "Generating random GidsApplet parameters and saving to %s",
        filename,
    )
    ret = GidsAppletParameters.generate()
    ret.write_toml(filename)
    return ret


def install_and_init_applet(
    gp: GP,
    gids: GidsApplet,
    gids_parameters: GidsAppletParameters,
    verbose=False,
    current_params: Optional[GPParameters] = None,
):
    """Install the GidsApplet and initialize it, setting pin."""
    log = _LOG.getChild("install_and_init_applet")
    # Try uninstalling first
    log.info("Uninstalling GidsApplet in case it already exists")
    gp.uninstall(
        gids.cap_file,
        current_params=current_params,
        verbose=verbose,
    )

    # Install applet
    log.info("Installing GidsApplet")
    gp.install(
        gids.cap_file,
        current_params=current_params,
        verbose=verbose,
    )
    # Init applet
    click.echo("\n\nPlease remove the card and re-insert it\n\n")

    log.info("Initializing GidsApplet")
    gids.init_card(
        gids_parameters,
        wait=True,
        verbose=verbose,
    )


@click.command()
@click.argument(
    "production_file",
    nargs=1,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True),
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    show_default=True,
    default=False,
    help="Verbose logging",
)
def produce(production_file, verbose):
    """Set up a card with GidsApplet and a key/certificate."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    log = _LOG.getChild("produce")

    with open(production_file, "r", encoding="utf-8") as fp:
        config_dict = toml.load(fp)
        config: ProcedureConfig = ProcedureConfig.from_dict(config_dict)  # type: ignore

    import pprint

    pprint.pprint(config)

    # Load or generate GP parameters, to lock the card when done
    current_gp_parameters: Optional[GPParameters] = None
    desired_gp_parameters: Optional[GPParameters] = None

    if config.gp_config.desired_parameters_filename:
        desired_gp_parameters = load_or_generate_gp_params(
            config.gp_config.desired_parameters_filename
        )

    if config.gp_config.current_parameters_filename:
        # This one must exists, makes no sense to generate the current keys randomly
        current_gp_parameters = GPParameters.load_toml(
            config.gp_config.current_parameters_filename
        )

    # Load GidsApplet init parameters
    gids_parameters = load_or_generate_gids_params(config.gids_parameters_filename)

    # Now that we finished parsing the config, we can start actually doing stuff.

    gids = GidsApplet()
    gp = GP()

    if config.install_and_init_gids:
        install_and_init_applet(
            gp,
            gids,
            gids_parameters,
            verbose=verbose,
            current_params=current_gp_parameters,
        )
    else:
        log.info("Skipping applet uninstall/reinstall")

    # Change lock key, if requested
    if desired_gp_parameters is None and current_gp_parameters is not None:
        log.info("Changing the GP lock key back to default")
        gp.lock_card(
            GPParameters(),
            current_params=current_gp_parameters,
            verbose=verbose,
        )
    elif (
        desired_gp_parameters is not None
        and desired_gp_parameters != current_gp_parameters
    ):
        log.info("Changing the GP lock key")
        gp.lock_card(
            desired_gp_parameters,
            current_params=current_gp_parameters,
            verbose=verbose,
        )

    loaded_keys = set(
        gids.enumerate_certificates(
            verbose=verbose,
        )
    )
    for loading in config.key_loading:
        if loading.label in loaded_keys:
            log.info(
                "Already have a certificate/key with label %s on the card, skipping",
                loading.label,
            )
        else:
            gids.import_key(
                gids_parameters,
                loading,
                verbose=verbose,
            )


if __name__ == "__main__":
    produce()
