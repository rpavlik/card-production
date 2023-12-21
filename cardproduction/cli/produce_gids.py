# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Set up a card with GidsApplet and a key/certificate."""

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional
from dataclasses_json import LetterCase, dataclass_json

import click
import toml

from ..gids import GidsApplet, GidsAppletKeyLoading, GidsAppletParameters
from ..gp import GPParameters, GP


_LOG = logging.getLogger(__name__)


@dataclass_json(letter_case=LetterCase.SNAKE)  # type: ignore
@dataclass
class ProcedureConfig:
    """Configure a card production procedure for the Gids applet."""

    gids_parameters_filename: str
    gp_parameters_filename: Optional[str] = None
    key_loading: List[GidsAppletKeyLoading] = field(default_factory=list)
    locked: bool = False
    skip_install: bool = False
    unlock: bool = False


def load_or_generate_gp_params(filename):
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


def load_or_generate_gids_params(filename):
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
    """Set up a card with GidsApplet and a key/certificate"""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    log = _LOG.getChild("produce")

    # yaml.register_class(Pkcs12)
    # yaml.register_class(GidsAppletKeyLoading)
    # yaml.register_class(ProcedureConfig)
    with open(production_file, "r", encoding="utf-8") as fp:
        # config: ProcedureConfig = yaml.load(fp)
        # config: dict[str, Any] = yaml.load(fp)
        config_dict: dict[str, Any] = toml.load(fp)
    import pprint

    pprint.pprint(config_dict)
    assert not isinstance(config_dict, list)
    config: ProcedureConfig = ProcedureConfig.from_dict(config_dict)  # type: ignore
    pprint.pprint(config)

    # Load or generate GP parameters, to lock the card when done
    current_gp_parameters = None
    gp_kwargs = dict()
    final_gp_parameters = None
    if config.gp_parameters_filename:
        final_gp_parameters = load_or_generate_gp_params(config.gp_parameters_filename)

    if config.locked:
        current_gp_parameters = final_gp_parameters
        gp_kwargs["current_params"] = current_gp_parameters

    # Load GidsApplet init parameters
    gids_parameters = load_or_generate_gids_params(config.gids_parameters_filename)

    # Now that we finished parsing the config, we can start actually doing stuff.

    gids = GidsApplet()
    gp = GP()

    if config.skip_install:
        log.info("Skipping applet uninstall/reinstall")
    else:
        install_and_init_applet(
            gp,
            gids,
            gids_parameters,
            verbose=verbose,
            current_params=current_gp_parameters,
        )

    # Change lock key, if requested
    if final_gp_parameters is not None and current_gp_parameters != final_gp_parameters:
        log.info("Changing the GP lock key")
        gp.lock_card(
            final_gp_parameters,
            current_params=current_gp_parameters,
            verbose=verbose,
        )
    elif config.locked and config.unlock:
        log.info("Changing the GP lock key back to default")
        gp.lock_card(
            GPParameters(),
            current_params=current_gp_parameters,
            verbose=verbose,
        )

    for loading in config.key_loading:
        gids.import_key(
            gids_parameters,
            loading,
            verbose=verbose,
        )


if __name__ == "__main__":
    produce()
