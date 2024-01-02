# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>

import logging
import secrets
import subprocess
from copy import copy
from dataclasses import dataclass
from typing import Iterable, Optional, Union

from dataclasses_json import dataclass_json
import toml

from .util import is_hex

_LOG = logging.getLogger(__name__)


@dataclass_json
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

    @classmethod
    def load_toml(cls, path):
        """Load a toml file containing this data."""
        with open(path, "r", encoding="utf-8") as fp:
            loaded = toml.load(fp)
        return cls.from_dict(loaded)  # type: ignore

    def write_toml(self, path):
        """Write a toml file containing this data."""
        with open(path, "w", encoding="utf-8") as fp:
            toml.dump(self.to_dict(), fp)  # type: ignore


class GP:
    """Wrapper for the GlobalPlatformPro command line tool."""

    def __init__(self, invocation_cmd: Union[str, Iterable[str], None] = None):
        """Initialize the GP tool wrapper object."""
        self._log = _LOG.getChild("GP")

        if invocation_cmd is None:
            self.invocation_cmd = ["java", "-jar", "gp.jar"]
        elif isinstance(invocation_cmd, str):
            self.invocation_cmd = [invocation_cmd]
        else:
            # some iterable
            self.invocation_cmd = list(invocation_cmd)

    def _make_cmd(
        self,
        verbose=False,
        current_params: Optional[GPParameters] = None,
    ):
        cmd = copy(self.invocation_cmd)
        if verbose:
            cmd.append("--verbose")
        if current_params:
            current_params.enforce_requirements()
            cmd.extend(("--key", current_params.key))
        return cmd

    def uninstall(self, cap_file, allow_failure=True, verbose=False, **kwargs):
        """Uninstall an applet."""
        cmd = self._make_cmd(verbose=verbose, **kwargs)
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

    def install(
        self,
        cap_file,
        default_selected=True,
        verbose=False,
        extra_args: Optional[list[str]] = None,
        **kwargs,
    ):
        """Install an applet."""
        cmd = self._make_cmd(verbose=verbose, **kwargs)
        cmd.extend(("--install", str(cap_file)))

        if default_selected:
            cmd.append("--default")

        if extra_args:
            cmd.extend(extra_args)

        self._log.info("Installing %s", cap_file)
        subprocess.check_call(cmd)

    def lock_card(
        self,
        new_params: GPParameters,
        current_params: Optional[GPParameters] = None,
        verbose=False,
    ):
        """Set the GP lock key."""
        if not current_params:
            # Use default
            current_params = GPParameters()
        new_params.enforce_requirements()
        self._log.info(
            "Changing GP lock key from %s to %s", current_params.key, new_params.key
        )

        cmd = self._make_cmd(verbose=verbose, current_params=current_params)
        cmd.extend(("--lock", new_params.key))
        subprocess.check_call(cmd)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    _LOG.info("Cycling lock key")

    random_key_params = GPParameters.generate()

    gp = GP()

    gp.lock_card(random_key_params, verbose=True)

    gp.lock_card(
        new_params=GPParameters(), current_params=random_key_params, verbose=True
    )
