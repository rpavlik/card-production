# Copyright 2023, Collabora, Ltd.
#
# SPDX-License-Identifier: GPL-3.0-only
"""General functionality without a better home."""


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
    return all(c in "01234567890" for c in s)
