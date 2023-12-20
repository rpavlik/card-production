# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only

import logging
import secrets
import subprocess
from pathlib import Path
from copy import copy
from dataclasses import dataclass

from .util import is_hex

_LOG = logging.getLogger(__name__)


@dataclass
class GPParameters:
    """
    Parameters required for GlobalPlatform usage.

    >>> GPParameters()
    GPParameters(key='404142434445464748494A4B4C4D4E4F')

    >>> GPParameters("404142434445464748494A4B4C4D4E4F")
    GPParameters(key='404142434445464748494A4B4C4D4E4F')

    >>> GPParameters("404142434445464748494a4b4c4d4e4f")
    GPParameters(key='404142434445464748494A4B4C4D4E4F')
    """

    key: str = "404142434445464748494A4B4C4D4E4F"  # 32 hex characters

    def __post_init__(self):
        """Check the requirements after init."""
        self.enforce_requirements()

    def enforce_requirements(self):
        """
        Raise an error if any of the fields do not meet requirements.
        """
        self.key = self.key.upper()
        # key
        if len(self.key) != 32:
            raise RuntimeError("Key must be 32 hex digits")
        if not is_hex(self.key):
            raise RuntimeError("Key number must be only hex digits")

    @classmethod
    def generate(cls):
        """
        Randomly generate suitable values and return an instance.

        >>> GPParameters.generate() != GPParameters()
        True
        """
        key = secrets.token_hex(16)
        return cls(key=key)


class GP:
    """Wrapper for the GlobalPlatformPro command line tool."""

    def __init__(self, invocation_cmd):
        """Initialize the GP tool wrapper object."""
        self._log = _LOG.getChild("GP")

        if invocation_cmd is None:
            self.invocation_cmd = ["java", "-jar", "gp.jar"]
        elif isinstance(invocation_cmd, str):
            self.invocation_cmd = [invocation_cmd]
        else:
            # some iterable
            self.invocation_cmd = list(invocation_cmd)

    def _make_cmd(self, verbose=False):
        cmd = copy(self.invocation_cmd)
        if verbose:
            cmd.append("--verbose")
        return cmd

    def uninstall(self, cap_file, allow_failure=True, verbose=False):
        """Uninstall an applet"""
        cmd = self._make_cmd(verbose=verbose)
        cmd.extend(("--uninstall", str(cap_file)))
        self._log.info("Uninstalling %s", cap_file)
        retcode = subprocess.call(cmd)
        if retcode != 0:
            if allow_failure:
                self._log.info(
                    "Uninstall of %s failed, maybe because it's not installed: "
                    "continuing anyway",
                    cap_file,
                )
            else:
                raise RuntimeError(f"Failed to uninstall {cap_file}")