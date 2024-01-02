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

from dataclasses_json import dataclass_json
import toml

from .util import is_hex

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


# @dataclass_json
# @dataclass
# class OpenPGPAppletParameters:
#     """Parameters required for initialization of a smartcard with an OpenPGP applet."""

#     pin: str  # 6 digits
#     admin_pin: str = "12345678"  # 8 digits

#     algo: str = "rsa4096"

#     def __post_init__(self):
#         """Check the requirements after init."""
#         self.check_requirements()

#     def check_requirements(self):
#         """Raise an error if any of the fields do not meet requirements."""
#         # Admin key
#         self.admin_pin = self.admin_pin.upper()
#         if len(self.admin_pin) != 8:
#             raise RuntimeError(f"Admin pin must be 8 digits, got '{self.admin_pin}'")
#         if not is_digits(self.admin_pin):
#             raise RuntimeError(f"Admin pin must be only digits, got '{self.admin_pin}'")

#         # PIN - this may be overly strict
#         if len(self.pin) != 6:
#             raise RuntimeError(f"PIN must be 6 decimal digits, got '{self.pin}'")
#         if not is_digits(self.pin):
#             raise RuntimeError(f"PIN must be only decimal digits, got '{self.pin}'")

#     @classmethod
#     def generate(cls):
#         """Randomly generate suitable values and return an instance."""
#         admin_pin = generate_decimal_pin(8)
#         sn = secrets.token_hex(4)
#         pin = generate_decimal_pin(6)
#         return cls(admin_pin=admin_pin, sn=sn, pin=pin)

#     @classmethod
#     def load_toml(cls, path):
#         """Load a toml file containing this data."""
#         with open(path, "r", encoding="utf-8") as fp:
#             loaded = toml.load(fp)
#         return cls.from_dict(loaded)  # type: ignore

#     def write_toml(self, path):
#         """Write a toml file containing this data."""
#         with open(path, "w", encoding="utf-8") as fp:
#             toml.dump(self.to_dict(), fp)  # type: ignore


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
