# Copyright 2023-2024, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
#
# Original author: Rylie Pavlik <rylie.pavlik@collabora.com>
"""General functionality without a better home."""

from random import randint
from typing import Optional


def is_hex(s: str) -> bool:
    """
    Return true if all characters are hex 'digits'.

    >>> is_hex("abcdef")
    True

    >>> is_hex("01234")
    True

    >>> is_hex("abcdef01234")
    True

    >>> is_hex("badf00d")
    True

    >>> is_hex("bad²f00d")
    False

    >>> is_hex("badf00d ")
    False

    >>> is_hex("feedthebed")
    False
    """
    return all(c in "01234567890abcdef" for c in s.lower())


# def check_length(param_name: str, param, required_)


def is_digits(s: str) -> bool:
    """
    Return true if all characters are just simple 0-9 digits.

    Cannot use isdigit because it's OK with calling things like
    exponents (e.g. ²) digits.

    >>> is_digits("abcdef")
    False

    >>> is_digits("01234")
    True

    >>> is_digits("abcdef01234")
    False

    >>> is_digits("badf00d")
    False

    >>> is_digits("badf00d ")
    False

    >>> is_digits("feedthebed")
    False
    """
    return all(c in "0123456789" for c in s)


def generate_decimal_pin(digits: int) -> str:
    """
    Return a random decimal pin with the requested number of digits.

    >>> len(generate_decimal_pin(5))
    5

    >>> len(generate_decimal_pin(8))
    8

    >>> is_digits(generate_decimal_pin(6))
    True
    """
    return "".join(str(randint(0, 9)) for _ in range(digits))


def handle_opensc_common_args(
    cmd: list[str],
    verbose: bool = False,
    wait: bool = False,
    reader: Optional[int] = None,
    aid: Optional[str] = None,
):
    """Extend cmd with all arguments required to apply the provided keyword args."""
    if verbose:
        cmd.append("--verbose")
    if wait:
        cmd.append("--wait")
    if reader is not None:
        cmd.extend(("--reader", str(reader)))
    if aid is not None:
        cmd.extend(("--aid", aid))
