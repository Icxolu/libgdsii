from __future__ import annotations

import dataclasses
import struct
import numpy as np
import datetime
import enum


class DateTime(datetime.datetime):
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


def _parse_line_width(options, ctx, layer):
    if options.get(layer, { }).get("line_width"):
        ctx.set_line_width(options[layer]["line_width"])
    elif options.get("line_width"):
        ctx.set_line_width(options["line_width"])

    return ctx


def _parse_font_size(options, ctx, layer):
    if options.get(layer, { }).get("font_size"):
        ctx.set_font_size(options[layer]["font_size"])
    elif options.get("font_size"):
        ctx.set_font_size(options["font_size"])

    return ctx


def _parse_stroke_color(options, ctx, layer):
    if options.get(layer, { }).get("stroke_color"):
        ctx.set_source_rgba(*options[layer]["stroke_color"])
    elif options.get("stroke_color"):
        ctx.set_source_rgba(*options["stroke_color"])
    else:
        ctx.set_source_rgb(0, 0, 0)  # black

    return ctx


def _get_fill_color(options, layer):
    if options.get(layer, { }).get("fill_color") is False:
        return Color(0, 0, 0, 0)  # transparent / no fill
    elif options.get(layer, { }).get("fill_color"):
        return options[layer]["fill_color"]
    elif options.get("fill_color"):
        return options["fill_color"]
    else:
        return Color(0, 0, 0, 0)  # transparent / no fill


def _parse_fill_color(options, ctx, layer):
    ctx.set_source_rgba(*_get_fill_color(options, layer))
    return ctx


def _parse_pattern(options, ctx, layer):
    import cairo

    col = _get_fill_color(options, layer)

    if options.get(layer, { }).get("pattern") is False:
        return ctx

    elif options.get(layer, { }).get("pattern") is not None:
        ctx.set_source_surface(options[layer]["pattern"](col))
        ctx.get_source().set_extend(cairo.EXTEND_REPEAT)

    elif options.get("pattern") is not None:
        ctx.set_source_surface(options["pattern"](col))
        ctx.get_source().set_extend(cairo.EXTEND_REPEAT)

    return ctx


@dataclasses.dataclass
class Color:
    r: float
    g: float
    b: float
    a: float = 1

    def __getitem__(self, key):
        if key == 0:
            return self.r
        elif key == 1:
            return self.g
        elif key == 2:
            return self.b
        elif key == 3:
            return self.a
        else:
            raise IndexError()


def _horizontal_lines_pattern(color: Color):
    import cairo

    pat = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, cairo.Rectangle(0, 0, 100, 3))
    ctx = cairo.Context(pat)
    ctx.set_line_width(.4)
    ctx.move_to(0, .5)
    ctx.line_to(100, .5)
    ctx.set_source_rgba(*color)
    ctx.stroke()

    return pat


def _vertical_lines_pattern(color: Color):
    import cairo

    pat = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, cairo.Rectangle(0, 0, 3, 100))
    ctx = cairo.Context(pat)
    ctx.set_line_width(.4)
    ctx.move_to(.5, 0)
    ctx.line_to(.5, 100)
    ctx.set_source_rgba(*color)
    ctx.stroke()

    return pat


def north_east_lines_pattern(color: Color):
    import cairo

    pat = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, cairo.Rectangle(0, 0, 3, 3))
    ctx = cairo.Context(pat)
    ctx.set_line_width(.4)
    ctx.move_to(1.3, -.2)
    ctx.line_to(3.2, 1.7)
    ctx.move_to(-.2, 1.3)
    ctx.line_to(1.7, 3.2)
    ctx.set_source_rgba(*color)
    ctx.stroke()

    return pat


def north_west_lines_pattern(color: Color):
    import cairo

    pat = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, cairo.Rectangle(0, 0, 3, 3))
    ctx = cairo.Context(pat)
    ctx.set_line_width(.4)
    ctx.move_to(-.2, 1.7)
    ctx.line_to(1.7, -.2)
    ctx.move_to(1.3, 3.2)
    ctx.line_to(3.2, 1.3)
    ctx.set_source_rgba(*color)
    ctx.stroke()

    return pat


class Pattern(enum.Enum):
    HORIZONTAL_LINES = _horizontal_lines_pattern
    VERTICAL_LINES = _vertical_lines_pattern
    NORTH_EAST_LINES = north_east_lines_pattern
    NORTH_WEST_LINES = north_west_lines_pattern
