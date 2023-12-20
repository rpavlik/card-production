# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
"""Working with the GidsApplet."""

import logging
import secrets
from random import randint
from dataclasses import dataclass
import subprocess
from pathlib import Path

from .util import is_digits, is_hex

_LOG = logging.getLogger(__name__)


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
            raise RuntimeError("Admin key must be 48 hex digits")
        if not is_hex(self.admin_key):
            raise RuntimeError("Admin key must be only hex digits")

        # Serial num
        self.sn = self.sn.upper()
        if len(self.sn) != 32:
            raise RuntimeError("Serial number must be 32 hex digits")
        if not is_hex(self.sn):
            raise RuntimeError("Serial number must be only hex digits")

        # PIN - this may be overly strict
        if len(self.pin) != 6:
            raise RuntimeError("PIN must be 6 decimal digits")
        if not is_digits(self.sn):
            raise RuntimeError("PIN must be only decimal digits")

    @classmethod
    def generate(cls):
        """Randomly generate suitable values and return an instance."""
        admin_key = secrets.token_hex(24)
        sn = secrets.token_hex(16)
        pin = "".join(str(randint(0, 9)) for _ in range(6))
        return cls(admin_key=admin_key, sn=sn, pin=pin)


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

    def _gids_tool(self, verbose=False, wait=False):
        cmd = ["gids-tool"]
        if verbose:
            cmd.append("--verbose")
        if wait:
            cmd.append("--wait")
        return cmd
