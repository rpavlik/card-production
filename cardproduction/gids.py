# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Working with the GidsApplet."""

import logging
import secrets
from random import randint
from dataclasses import dataclass
import subprocess
from pathlib import Path

from dataclasses_json import dataclass_json

from .pkcs12 import Pkcs12
from .util import is_digits, is_hex

_LOG = logging.getLogger(__name__)

@dataclass_json
@dataclass
class GidsAppletParameters:
    """Parameters required for initialization of a smartcard running GidsApplet."""

    admin_key: str  # 48 hex characters
    sn: str  # 16 hex characters
    pin: str  # 6 digits

    def __post_init__(self):
        """Check the requirements after init."""
        self.check_requirements()

    def check_requirements(self):
        """Raise an error if any of the fields do not meet requirements."""
        # Admin key
        self.admin_key = self.admin_key.upper()
        if len(self.admin_key) != 48:
            raise RuntimeError(
                f"Admin key must be 48 hex digits, got '{self.admin_key}'"
            )
        if not is_hex(self.admin_key):
            raise RuntimeError(
                f"Admin key must be only hex digits, got '{self.admin_key}'"
            )

        # Serial num
        self.sn = self.sn.upper()
        if len(self.sn) != 32:
            raise RuntimeError(f"Serial number must be 32 hex digits, got '{self.sn}'")
        if not is_hex(self.sn):
            raise RuntimeError(
                f"Serial number must be only hex digits, got '{self.sn}'"
            )

        # PIN - this may be overly strict
        if len(self.pin) != 6:
            raise RuntimeError(f"PIN must be 6 decimal digits, got '{self.pin}'")
        if not is_digits(self.pin):
            raise RuntimeError(f"PIN must be only decimal digits, got '{self.pin}'")

    @classmethod
    def generate(cls):
        """Randomly generate suitable values and return an instance."""
        admin_key = secrets.token_hex(24)
        sn = secrets.token_hex(16)
        pin = "".join(str(randint(0, 9)) for _ in range(6))
        return cls(admin_key=admin_key, sn=sn, pin=pin)


@dataclass_json
@dataclass
class GidsAppletKeyLoading:
    """Parameters for loading a secret key and certificate into a GIDS applet"""

    label: str
    key: Pkcs12


class GidsApplet:
    """Perform interactions with the GidsApplet."""

    def __init__(self, cap_file="GidsApplet-import4k-1.3-20231219.cap"):
        """Initialize general parameters about the applet"""
        self.cap_file = Path(cap_file)
        if not self.cap_file.exists():
            raise RuntimeError(f"Could not find GidApplet cap file {cap_file}")

        self._log = _LOG.getChild("GidsApplet")
        self._log.debug("Will use cap file %s", cap_file)

    def init_card(self, params: GidsAppletParameters, verbose=False, wait=False):
        """Initialize the card with the given parameters."""
        params.check_requirements()

        self._log.info("Initializing GidsApplet")
        cmd = self._gids_tool(verbose=verbose, wait=wait)
        cmd.extend(
            (
                "--initialize",
                "--admin-key",
                params.admin_key,
                "--pin",
                params.pin,
                "--serial-number",
                params.sn,
            )
        )
        subprocess.check_call(cmd)

    def import_key(
        self, params: GidsAppletParameters, loading: GidsAppletKeyLoading, verbose=False
    ):
        """Import private key and certificate from p12 file"""
        cmd = ["pkcs15-init"]
        if verbose:
            cmd.append("-v")
        cmd.extend(
            (
                "--verify-pin",
                "--pin",
                params.pin,
                "--store-private-key",
                loading.key.filename,
                "--format",
                "pkcs12",
                "--auth-id",
                "80",
                "--label",
                loading.label,
            )
        )
        if loading.key.passphrase:
            cmd.extend(("--passphrase", loading.key.passphrase))

        self._log.info("Importing %s as %s", loading.key.filename, loading.label)
        subprocess.check_call(cmd)

    def _gids_tool(self, verbose=False, wait=False):
        cmd = ["gids-tool"]
        if verbose:
            cmd.append("--verbose")
        if wait:
            cmd.append("--wait")
        return cmd
