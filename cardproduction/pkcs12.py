# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Data relating to pkcs12."""


from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Pkcs12:
    """Represent a PKCS#12 file with private key and certificate."""

    filename: str
    passphrase: Optional[str] = None
