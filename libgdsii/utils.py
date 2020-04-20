from __future__ import annotations

import struct
import numpy as np


class DateTime:
    def __init__(self, year, month, day, hour, minute, second):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second

    def __str__(self):
        return f"{self.day}/{self.month}/{self.year} {self.hour}:{self.minute}:{self.second}"

    def pack(self) -> bytes:
        return struct.pack(">6h", self.year, self.month, self.day, self.hour, self.minute, self.second)


def eight_byte_real_to_float(value: bytes) -> float:
    """
    Convert a number from GDSII 8 byte real format to float.
    Parameters
    ----------
    value : bytes
        The GDSII binary string representation of the number.
    Returns
    -------
    out : float
        The number represented by `value`.
    """

    # exponent is the first of the 8 bytes (signed) in Excess-64 representation
    exponent, = struct.unpack(">B7x", value)

    # extract sign, first bit of exponent byte
    mask = 1 << 7
    sgn = -1 if exponent & mask else 1
    exponent &= ~mask

    exponent -= 64  # calculate the real exponent

    # the mantissa are the 7 last bytes. To make our life easier we repack it
    # as 8 bytes with a trailing zero byte and unpack it as a longlong
    mantissa = struct.pack(">8B", 0, *struct.unpack(">x7B", value))
    mantissa, = struct.unpack(">Q", mantissa)
    mantissa *= 2 ** -56  # rescale into fractional representation

    return sgn * mantissa * 16 ** exponent


def float_to_eight_byte_real(value: float) -> bytes:
    """
    Converts a float into the GDSII 8 byte real format.
    Parameters
    ----------
    value : float

    Returns
    -------
    out : float
        The GDSII binary string representation of value.
    """
    if value == 0:
        return struct.pack(">Q", 0)

    if value < 0:
        sgn = 1
        value = -value
    else:
        sgn = 0

    exponent = int(np.ceil(np.log2(value) / 4))
    mantissa = value / 16 ** exponent

    exponent += 64
    mantissa *= 2 ** 56

    # first bit in the byte for exponent is the sign
    mask = 1 << 7
    exponent &= ~mask
    if sgn == 1: exponent |= mask

    exponent_packed = struct.pack(">B", exponent)
    mantissa_packed = struct.pack(">Q", int(mantissa))
    return exponent_packed + mantissa_packed[1:]
