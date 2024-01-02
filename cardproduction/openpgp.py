# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Working with the SmartPGP OpenPGP applet."""

import logging
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import tempfile
import subprocess

from dataclasses_json import dataclass_json
import toml

from .util import generate_decimal_pin, is_digits, is_hex

_LOG = logging.getLogger(__name__)


@dataclass_json
@dataclass
class OpenPGPAppletInstallParameters:
    """Parameters required for installation of an OpenPGP applet on a smartcard."""

    sn: str  # 8 hex characters

    # 4 hex characters
    # anything in fff0 to fffe is for unmanaged random assignment of serial numbers
    manufacturer_code: str = "fff5"

    def __post_init__(self):
        """Check the requirements after init."""
        self.check_requirements()

    def is_manufacturer_reserved_for_random_sn(self):
        """Check if the manufacturer code is for unmanaged random serial numbers."""
        # checking in here since we require these assumptions to be true
        self._check_mfr_code_requirements()

        return (
            self.manufacturer_code.startswith("fff")
            and self.manufacturer_code[-1] != "f"
        )

    def _check_mfr_code_requirements(self):
        self.manufacturer_code = self.manufacturer_code.lower()
        if len(self.manufacturer_code) != 4:
            raise RuntimeError(
                f"Manufacturer must be 4 hex digits, got '{self.manufacturer_code}'"
            )
        if not is_hex(self.manufacturer_code):
            raise RuntimeError(
                f"Manufacturer must be only hex digits, got '{self.manufacturer_code}'"
            )

    def check_requirements(self):
        """Raise an error if any of the fields do not meet requirements."""
        # Serial num
        self.sn = self.sn.upper()
        if len(self.sn) != 8:
            raise RuntimeError(f"Serial number must be 8 hex digits, got '{self.sn}'")
        if not is_hex(self.sn):
            raise RuntimeError(
                f"Serial number must be only hex digits, got '{self.sn}'"
            )

        self._check_mfr_code_requirements()
        in_random_range = self.is_manufacturer_reserved_for_random_sn()
        if not in_random_range:
            _LOG.warning(
                "Specified manufacturer code %s is not in the unmanaged "
                "random SN assignment range, and msut be registered!",
                self.manufacturer_code,
            )

    @classmethod
    def generate(cls, manufacturer_code="fff5"):
        """Randomly generate suitable values and return an instance."""
        sn = secrets.token_hex(4)
        ret = cls(sn=sn)
        if not ret.is_manufacturer_reserved_for_random_sn():
            raise RuntimeError(
                "The specified manufacturer code is not reserved for random assignment."
            )
        return ret

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


@dataclass_json
@dataclass
class OpenPGPPins:
    """Parameters required for initialization of a smartcard with an OpenPGP applet."""

    pin: str = "123456"  # 6+ digits
    admin_pin: str = "12345678"  # 8 digits

    def __post_init__(self):
        """Check the requirements after init."""
        self.check_requirements()

    def check_requirements(self):
        """Raise an error if any of the fields do not meet requirements."""
        # Admin pin
        if len(self.admin_pin) < 8 or len(self.admin_pin) > 127:
            raise RuntimeError(
                f"Admin pin must be 8-127 digits, got '{self.admin_pin}'"
            )
        if not is_digits(self.admin_pin):
            raise RuntimeError(f"Admin pin must be only digits, got '{self.admin_pin}'")

        # PIN - this may be overly strict
        if len(self.pin) < 6 or len(self.pin) > 127:
            raise RuntimeError(f"PIN must be 6-127 decimal digits, got '{self.pin}'")
        if not is_digits(self.pin):
            raise RuntimeError(f"PIN must be only decimal digits, got '{self.pin}'")

    @classmethod
    def generate(cls) -> "OpenPGPPins":
        """Randomly generate suitable values and return an instance."""
        admin_pin = generate_decimal_pin(8)
        pin = generate_decimal_pin(6)
        return cls(admin_pin=admin_pin, pin=pin)

    @classmethod
    def load_toml(cls, path) -> "OpenPGPPins":
        """Load a toml file containing this data."""
        with open(path, "r", encoding="utf-8") as fp:
            loaded = toml.load(fp)
        return cls.from_dict(loaded)  # type: ignore

    def write_toml(self, path):
        """Write a toml file containing this data."""
        with open(path, "w", encoding="utf-8") as fp:
            toml.dump(self.to_dict(), fp)  # type: ignore


def _make_pin_ascii_string(pin: str, delim: str = ""):
    """
    Convert PIN strings to the format needed by opensc-explorer.

    >>> _make_pin_ascii_string("12345678")
    '3132333435363738'

    >>> _make_pin_ascii_string("123456", ":")
    '31:32:33:34:35:36'

    """
    return delim.join(f"{ord(digit):02x}" for digit in pin)


class SmartPGPApplet:
    """Perform interactions with the SmartPGP applet."""

    def __init__(
        self,
        cap_file="SmartPGP-v1.22.2-jc304-without_sm-rsa_up_to_4096.cap",
    ):
        """Initialize general parameters about the applet."""
        # smartpgp_parent_dir = Path(__file__).parent.resolve().parent / "vendor"
        # if not (smartpgp_parent_dir / "smartpgp" / "highlevel.py").exists():
        #     raise RuntimeError(
        #         f"Could not find smartpgp Python module in {smartpgp_parent_dir}"
        #     )

        # sys.path.append(str(smartpgp_parent_dir))

        # import smartpgp.highlevel as pgp

        self.cap_file = Path(cap_file)
        if not self.cap_file.exists():
            raise RuntimeError(f"Could not find SmartPGP cap file {cap_file}")

        self._log = _LOG.getChild("SmartPGPApplet")
        self._log.debug("Will use cap file %s", cap_file)

    def compute_extra_args(self, params: OpenPGPAppletInstallParameters):
        """Compute the "extra_args" list for GP.install."""
        params.check_requirements()
        aid = f"d276000124010304{params.manufacturer_code}{params.sn}0000"
        return ["--create", aid]

    def change_pins(
        self,
        desired_pins: OpenPGPPins,
        current_pins: Optional[OpenPGPPins] = None,
        verbose=False,
        wait=False,
    ):
        """Change the user and admin pins."""
        if not current_pins:
            current_pins = OpenPGPPins()

        current_admin_pin_ascii = _make_pin_ascii_string(current_pins.admin_pin)
        current_admin_pin_ascii_colons = _make_pin_ascii_string(
            current_pins.admin_pin, ":"
        )

        current_pin_ascii_colons = _make_pin_ascii_string(current_pins.pin, ":")

        cmds = [
            f"verify CHV3 {current_admin_pin_ascii}\n",
            f'change CHV1 {current_pin_ascii_colons} "{desired_pins.pin}"\n',
            f'change CHV3 {current_admin_pin_ascii_colons} "{desired_pins.admin_pin}"',
        ]

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as script:
            try:
                script.writelines(cmds)
                script.close()

                self._log.info(f"Wrote commands to {script.name}")
                args = ["opensc-explorer", "--card-driver", "openpgp"]
                if verbose:
                    args.append("--verbose")
                if wait:
                    args.append("--wait")
                args.append(script.name)
                subprocess.check_call(args)
            finally:
                Path(script.name).unlink()
