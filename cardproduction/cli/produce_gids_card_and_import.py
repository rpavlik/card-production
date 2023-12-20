# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Set up a card with GidsApplet and a key/certificate."""

import dataclasses
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

from ruamel.yaml import YAML
import click

from cardproduction.pkcs12 import Pkcs12

from ..gids import GidsApplet, GidsAppletKeyLoading, GidsAppletParameters
from ..gp import GPParameters, GP


_LOG = logging.getLogger(__name__)


@dataclass
class ProcedureConfig:
    """Configure a card production procedure for the Gids applet."""

    gids_parameters_filename: str
    gp_parameters_filename: Optional[str] = None
    key_loading: List[GidsAppletKeyLoading] = field(default_factory=list)
    # key_loading: List[Any] = field(default_factory=list)


def load_or_generate_gp_params(yaml, filename):
    log = _LOG.getChild("load_or_generate_gp_params")
    loaded = None
    try:
        log.info(
            "Attempting to load GP parameters from %s",
            filename,
        )
        with open(filename, "r", encoding="utf-8") as fp:
            loaded = yaml.load(fp)
    except FileNotFoundError:
        pass
    if loaded:
        return GPParameters(**loaded)

    log.info(
        "Generating random GP parameters and saving to %s",
        filename,
    )
    ret = GPParameters.generate()
    with open(filename, "w", encoding="utf-8") as fp:
        yaml.dump(dataclasses.asdict(ret), fp)
    return ret


def load_or_generate_gids_params(yaml, filename):
    log = _LOG.getChild("load_or_generate_gids_params")
    loaded = None
    try:
        log.info(
            "Attempting to load GidsApplet init parameters from %s",
            filename,
        )
        with open(filename, "r", encoding="utf-8") as fp:
            loaded = yaml.load(fp)
    except FileNotFoundError:
        # _LOG.info(
        #     "Not found, generating and saving instead."
        # )
        pass
    if loaded:
        return GidsAppletParameters(**loaded)

    log.info(
        "Generating random GidsApplet parameters and saving to %s",
        filename,
    )
    ret = GidsAppletParameters.generate()
    with open(filename, "w", encoding="utf-8") as fp:
        yaml.dump(dataclasses.asdict(ret), fp)
    return ret


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
    kwargs = {"verbose": verbose}

    yaml = YAML(typ="safe")
    # yaml.register_class(Pkcs12)
    # yaml.register_class(GidsAppletKeyLoading)
    # yaml.register_class(ProcedureConfig)
    with open(production_file, "r", encoding="utf-8") as fp:
        # config: ProcedureConfig = yaml.load(fp)
        config: dict[str, Any] = yaml.load(fp)
    import pprint

    pprint.pprint(config)
    assert not isinstance(config, list)

    # Load or generate GP parameters, to lock the card when done
    gp_parameters = None
    gp_param_fn = config.get("gp_parameters_filename")
    if gp_param_fn:
        gp_parameters = load_or_generate_gp_params(yaml, gp_param_fn)

    # Load GidsApplet init parameters
    gids_parameters = load_or_generate_gids_params(
        yaml, config["gids_parameters_filename"]
    )

    gids = GidsApplet()
    gp = GP()

    # Install applet
    log.info("Installing GidsApplet")
    gp.install(gids.cap_file, **kwargs)

    # Change lock key, if requested
    if gp_parameters is not None:
        log.info("Changing the GP lock key")
        gp.lock_card(gp_parameters, **kwargs)

    # Init applet
    click.echo("\n\nPlease remove the card and re-insert it\n\n")
    log.info("Initializing GidsApplet")
    gids.init_card(gids_parameters, wait=True, **kwargs)

    for loading in config.get("key_loading", []):
        pkcs12 = Pkcs12(**loading["key"])
        label = loading["label"]
        gids.import_key(
            gids_parameters,
            GidsAppletKeyLoading(
                label=label,
                key=pkcs12,
            ),
            **kwargs
        )


if __name__ == "__main__":
    produce()
