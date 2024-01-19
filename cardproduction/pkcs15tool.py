# Copyright 2023-2024, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""Working with pkcs15-tool."""

import logging
import re
import subprocess

from .util import handle_opensc_common_args


_LOG = logging.getLogger(__name__)
_CERT_LABEL_RE = re.compile(r"^X.509 Certificate \[(?P<label>[^\]]+)]$")


class Pkcs15Tool:
    """Generic pkcs15-tool interaction."""

    def __init__(self, pkcs15tool: str = "pkcs15-tool") -> None:
        """Initialize logger in tool."""
        self._pkcs15tool = pkcs15tool
        self._log = _LOG.getChild("Pkcs15Tool")

    def enumerate_certificates(self, verbose=False, **kwargs) -> list[str]:
        """Get a list of key/certificate labels."""
        cmd = [self._pkcs15tool, "--list-certificates"]
        handle_opensc_common_args(cmd, verbose=verbose, **kwargs)
        output = subprocess.check_output(cmd)

        ret = []
        for line in output.splitlines():
            m = _CERT_LABEL_RE.match(line.decode().strip())
            if m:
                ret.append(m["label"])
        return ret


if __name__ == "__main__":
    tool = Pkcs15Tool()
    labels = tool.enumerate_certificates()
    print(labels)
