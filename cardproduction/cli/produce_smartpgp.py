# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Set up a card with SmartPGP."""

import logging
from dataclasses import dataclass, field
import subprocess
from typing import Optional
from dataclasses_json import LetterCase, dataclass_json

import click
import toml

from .common import GPConfig, load_or_generate_gp_params
from ..openpgp import OpenPGPAppletInstallParameters, OpenPGPPins, SmartPGPApplet
from ..gp import GPParameters, GP


_LOG = logging.getLogger(__name__)


@dataclass_json(letter_case=LetterCase.SNAKE)  # type: ignore
@dataclass
class PinConfig:
    """Parameters for setting pins."""

    current_pins_filename: Optional[str] = None
    desired_pins_filename: Optional[str] = None


@dataclass_json(letter_case=LetterCase.SNAKE)  # type: ignore
@dataclass
class ProcedureConfig:
    """Configure a card production procedure for the SmartPGP applet."""

    openpgp_install_parameters_filename: str
    install_smartpgp: bool
    gp_config: GPConfig = field(default_factory=GPConfig)
    pin_config: PinConfig = field(default_factory=PinConfig)
    # key_loading: List[GidsAppletKeyLoading] = field(default_factory=list)


def load_or_generate_openpgp_install_params(filename) -> OpenPGPAppletInstallParameters:
    """Load an OpenPGP install parameters file, if one exists, or generate one."""
    log = _LOG.getChild("load_or_generate_openpgp_install_params")
    loaded = None
    try:
        log.info(
            "Attempting to load OpenPGP install parameters from %s",
            filename,
        )
        loaded = OpenPGPAppletInstallParameters.load_toml(filename)
    except FileNotFoundError:
        pass
    if loaded:
        return loaded

    log.info(
        "Generating random OpenPGP card serial number and saving parameters to %s",
        filename,
    )
    ret = OpenPGPAppletInstallParameters.generate()
    ret.write_toml(filename)
    return ret


def load_or_generate_openpgp_pins(filename) -> OpenPGPPins:
    """Load an OpenPGP pins file, if one exists, or generate one."""
    log = _LOG.getChild("load_or_generate_openpgp_pins")
    loaded = None
    try:
        log.info(
            "Attempting to load OpenPGP pins from %s",
            filename,
        )
        loaded = OpenPGPPins.load_toml(filename)
    except FileNotFoundError:
        pass
    if loaded:
        return loaded

    log.info(
        "Generating random OpenPGP pins and saving to %s",
        filename,
    )
    ret = OpenPGPPins.generate()
    ret.write_toml(filename)
    return ret


def install_and_init_applet(
    gp: GP,
    smartpgp: SmartPGPApplet,
    install_params: OpenPGPAppletInstallParameters,
    verbose=False,
    current_params: Optional[GPParameters] = None,
):
    """Install the SmartPGP applet with the specified serial number."""
    log = _LOG.getChild("install_and_init_applet")
    # Try uninstalling first
    log.info("Uninstalling OpenPGP in case it already exists")
    gp.uninstall(
        smartpgp.cap_file,
        current_params=current_params,
        verbose=verbose,
    )

    # Install applet
    log.info("Installing SmartPGP with serial number %s", install_params.sn)
    gp.install(
        smartpgp.cap_file,
        current_params=current_params,
        verbose=verbose,
        extra_args=smartpgp.compute_extra_args(install_params),
    )
    # Init applet
    click.echo("\n\nPlease remove the card and re-insert it\n\n")

    subprocess.check_call(["openpgp-tool", "--card-info", "--verbose", "--wait"])


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
    """Set up a card with SmartPGP."""
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

    # Load OpenPGP install parameters
    install_params = load_or_generate_openpgp_install_params(
        config.openpgp_install_parameters_filename
    )

    # Load or generate pins, to change if desired
    current_pins: Optional[OpenPGPPins] = None
    desired_pins: Optional[OpenPGPPins] = None

    if config.pin_config.desired_pins_filename:
        desired_pins = load_or_generate_openpgp_pins(
            config.pin_config.desired_pins_filename
        )

    if config.pin_config.current_pins_filename:
        # This one must exists, makes no sense to generate the current keys randomly
        desired_pins = OpenPGPPins.load_toml(config.pin_config.current_pins_filename)

    # Now that we finished parsing the config, we can start actually doing stuff.

    smartpgp = SmartPGPApplet()
    gp = GP()

    if config.install_smartpgp:
        install_and_init_applet(
            gp,
            smartpgp,
            install_params,
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

    # Change pins, if requested
    if desired_pins is not None and desired_pins != current_pins:
        log.info("Changing the pins")
        smartpgp.change_pins(
            desired_pins,
            current_pins=current_pins,
            verbose=verbose,
        )


if __name__ == "__main__":
    produce()
