from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    import libgdsii.library as library

import enum
import struct
import warnings
import numpy as np

import libgdsii.utils as utils
import libgdsii.gdstypes as gdstypes
import libgdsii.exceptions as exceptions


class Record:
    record_type: gdstypes.RecordType
    data_type: gdstypes.DataType

    @classmethod
    def read(cls, record: library.RawRecord) -> Record:
        cls._check(record)

    def pack(self) -> bytes:
        """
        used to pack the record data
        :return: the packed data
        """
        raise NotImplementedError()

    def write(self, stream: typing.BinaryIO):
        """
        writes the record to the output stream
        :param stream: the output stream
        """
        data = self.pack()
        header = struct.pack(">HBB", len(data) + 4, self.record_type.value, self.data_type.value)
        stream.write(header)
        stream.write(data)

    @classmethod
    def _check(cls: Record, record: library.RawRecord):
        """
        checks whether the read record matches the expected one, also checks for matching datatypes
        :param record: The read record
        """
        if cls.record_type is not record.record_type:
            raise exceptions.UnexpectedRecordException(cls.record_type, record.record_type)
        if cls.data_type is not record.data_type:
            warnings.warn(exceptions.DatatypeMismatchWarning(cls.data_type, record.data_type))


class SimpleRecord(Record):
    data_type = gdstypes.DataType.NO_DATA_PRESENT

    @classmethod
    def read(cls, record: library.RawRecord) -> SimpleRecord:
        super().read(record)
        self = cls.__new__(cls)
        return self

    def pack(self) -> bytes:
        return b""


class HEADER(Record):
    """
    Contains two bytes of data representing the version number.
    """
    record_type = gdstypes.RecordType.HEADER
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    version: gdstypes.Version

    def __init__(self, version: gdstypes.Version):
        self.version = version

    @classmethod
    def read(cls, record: library.RawRecord) -> HEADER:
        super()._check(record)
        data, = struct.unpack(">h", record.data)

        self = cls.__new__(cls)
        self.version = gdstypes.Version(data)
        return self

    def __str__(self):
        return str(self.version)

    def pack(self) -> bytes:
        return struct.pack(">h", self.version.value)


class BGNLIB(Record):
    """
    Contains last modification time of library (two bytes each for year, month, day, hour, minute,and second)
    as well as time of last access (same format) and marks beginning of library.
    """
    record_type = gdstypes.RecordType.BGNLIB
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    modification_date: utils.DateTime
    access_date: utils.DateTime

    def __init__(self, mod_date: utils.DateTime, acc_date: utils.DateTime):
        self.modification_date = mod_date
        self.access_date = acc_date

    @classmethod
    def read(cls, record: library.RawRecord) -> BGNLIB:
        super().read(record)
        self = cls.__new__(cls)
        self.modification_date = utils.DateTime(*struct.unpack(">6h12x", record.data))
        self.access_date = utils.DateTime(*struct.unpack(">12x6h", record.data))
        return self

    def __str__(self):
        return f"(Library) last modified: {self.modification_date}, last accessed: {self.access_date}"

    def pack(self) -> bytes:
        mod_date_packed = self.modification_date.pack()
        acc_date_packed = self.access_date.pack()
        return mod_date_packed + acc_date_packed


class LIBNAME(Record):
    """
    Contains a string which is the library name. The library name must adhere to CDOS file name
    conventions for length and valid characters. The library name may include the file extension
    """
    record_type = gdstypes.RecordType.LIBNAME
    data_type = gdstypes.DataType.ASCII_STRING

    name: str

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def read(cls, record: library.RawRecord) -> LIBNAME:
        super().read(record)
        self = cls.__new__(cls)
        self.name = record.data.decode(encoding = "ascii").rstrip("\0")
        return self

    def __str__(self):
        return f"library {self.name}"

    def pack(self) -> bytes:
        return self.name.encode(encoding = "ascii") + b"\0"


class UNITS(Record):
    """
    Contains 2 8-byte real numbers. The first is the size of a database unit in user units.
    The second is the size of a database unit in meters. For example, if your library was
    created with the default units (user unit = 1 micron and 1000 database units per user unit),
    then the first number would be .001 and the second number would be 1E-9.
    Typically, the first number is less than 1, since you use more than 1 database unit per user unit
    """
    record_type = gdstypes.RecordType.UNITS
    data_type = gdstypes.DataType.EIGHT_BYTE_REAL

    logical_unit: float
    physical_unit: float

    def __init__(self, logical_unit: float, physical_unit: float):
        self.logical_unit = logical_unit
        self.physical_unit = physical_unit

    @classmethod
    def read(cls, record: library.RawRecord) -> UNITS:
        super().read(record)
        self = cls.__new__(cls)
        self.logical_unit = utils.eight_byte_real_to_float(record.data[:8])
        self.physical_unit = utils.eight_byte_real_to_float(record.data[8:])
        return self

    def __str__(self):
        return f"unit in user units: {self.logical_unit}, units in meters: {self.physical_unit}"

    def pack(self) -> bytes:
        logical_unit_packed = utils.float_to_eight_byte_real(self.logical_unit)
        physical_unit_packed = utils.float_to_eight_byte_real(self.physical_unit)
        return logical_unit_packed + physical_unit_packed


class BGNSTR(Record):
    """
    Contains creation time and last modification time of a structure and marks the beginning of a structure.
    """
    record_type = gdstypes.RecordType.BGNSTR
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    modification_date: utils.DateTime
    access_date: utils.DateTime

    def __init__(self, mod_date: utils.DateTime, acc_date: utils.DateTime):
        self.modification_date = mod_date
        self.access_date = acc_date

    @classmethod
    def read(cls, record: library.RawRecord) -> BGNSTR:
        super().read(record)
        self = cls.__new__(cls)
        self.modification_date = utils.DateTime(*struct.unpack(">6h12x", record.data))
        self.access_date = utils.DateTime(*struct.unpack(">12x6h", record.data))
        return self

    def __str__(self):
        return f"(Structure) last modified: {self.modification_date}, last accessed: {self.access_date}"

    def pack(self) -> bytes:
        mod_date_packed = self.modification_date.pack()
        acc_date_packed = self.access_date.pack()
        return mod_date_packed + acc_date_packed


class STRNAME(Record):
    """
    Contains a string which is the structure name. A structure name may be up to 32 characters long.
    Legal structure name characters are:
    • A through Z
    • a through z
    • 0 through 9
    • Underscore (_)
    • Question mark (?)
    • Dollar sign ($)
    """
    record_type = gdstypes.RecordType.STRNAME
    data_type = gdstypes.DataType.ASCII_STRING

    name: str

    def __init__(self, name: str):
        self.name = name

    @classmethod
    def read(cls, record: library.RawRecord) -> STRNAME:
        super().read(record)
        self = cls.__new__(cls)
        self.name = record.data.decode(encoding = "ascii").rstrip("\0")
        return self

    def __str__(self):
        return f"structure {self.name}"

    def pack(self) -> bytes:
        return self.name.encode(encoding = "ascii") + b"\0"


class BOUNDARY(SimpleRecord):
    """
    Marks the beginning of a boundary element
    """
    record_type = gdstypes.RecordType.BOUNDARY


class LAYER(Record):
    """
    Contains 2 bytes which specify the layer. The value of the layer must be in the range of a to 63.
    """
    record_type = gdstypes.RecordType.LAYER
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    layer: int

    def __init__(self, layer: int):
        self.layer = layer

    @classmethod
    def read(cls, record: library.RawRecord) -> LAYER:
        super().read(record)
        self = cls.__new__(cls)
        self.layer, = struct.unpack(">h", record.data)
        return self

    def __str__(self):
        return f"Layer #{self.layer}"

    def pack(self) -> bytes:
        return struct.pack(">h", self.layer)


class DATATYPE(Record):
    """
    Contains 2 bytes which specify datatype. The value of the datatype must be in the range of a to 63.
    """
    record_type = gdstypes.RecordType.DATATYPE
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    type: gdstypes.DataType

    def __init__(self, type: gdstypes.DataType):
        self.type = type

    @classmethod
    def read(cls, record: library.RawRecord) -> DATATYPE:
        super().read(record)
        self = cls.__new__(cls)
        self.type = gdstypes.DataType(struct.unpack(">h", record.data)[0])
        return self

    def __str__(self):
        return f"Data type: {str(self.data_type)}"

    def pack(self) -> bytes:
        return struct.pack(">h", self.type.value)


class XY(Record):
    """
    Contains an array of XY coordinates in database units. Each X or Y coordinate is four bytes long.
    Path and boundary elements may have up to 200 pairs of coordinates. A path must have at least 2,
    and a boundary at least 4 pairs of coordinates. The first and last point of a boundary must coincide.
    A text or SREF element must have only one pair of coordinates. An AREF has exactly three pairs of
    coordinates, which specify the orthogonal array lattice. In an AREF the first point is the array
    reference point. The second point locates a position which is displaced from the reference point
    by the inter-column spacing times the number of columns. The third point locates a position which
     is displaced from the reference point by the inter-row spacing times the number of rows. A node may
    have from 1 to 50 pairs of coordinates. A box must have five pairs of coordinates with the first
    and last points coinciding.
    """
    record_type = gdstypes.RecordType.XY
    data_type = gdstypes.DataType.FOUR_BYTE_SIGNED_INTEGER

    x: np.ndarray[int]
    y: np.ndarray[int]

    def __init__(self):
        self.x = np.array([])
        self.y = np.array(([]))

    @classmethod
    def read(cls, record: library.RawRecord) -> XY:
        super().read(record)
        self = cls.__new__(cls)
        x = []
        y = []

        size = len(record.data)
        for i in range(size // 8):
            xi, yi = struct.unpack(">ll", record.data[8 * i:8 * (i + 1)])
            x.append(xi)
            y.append(yi)

        self.x = np.array(x)
        self.y = np.array(y)

        return self

    def __str__(self):
        return ", ".join([f"({x}, {y})" for x, y in zip(self.x, self.y)])

    def pack(self) -> bytes:
        tmp = [None] * 2 * self.x.size
        tmp[::2] = self.x
        tmp[1::2] = self.y
        tmp = np.array(tmp).astype(np.int32)
        return struct.pack(f">{2 * self.x.size}l", *tmp)


class ENDEL(SimpleRecord):
    """
    Marks the end of an element.
    """
    record_type = gdstypes.RecordType.ENDEL


class BOX(SimpleRecord):
    """
    Marks the beginning of a box element.
    """
    record_type = gdstypes.RecordType.BOX


class BOXTYPE(Record):
    """
    Contains 2 bytes which specify boxtype. The value of the boxtype must be in the range of 0 to 63.
    """
    record_type = gdstypes.RecordType.BOXTYPE
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    type: int

    def __init__(self, type: int):
        self.type = type

    @classmethod
    def read(cls, record: library.RawRecord) -> BOXTYPE:
        super().read(record)
        self = cls.__new__(cls)
        self.type, = struct.unpack(">h", record.data)
        return self

    def __str__(self):
        return f"box type: {self.type}"

    def pack(self) -> bytes:
        return struct.pack(">h", self.type)


class TEXT(SimpleRecord):
    """
    Marks the beginning of a text element.
    """
    record_type = gdstypes.RecordType.TEXT


class TEXTTYPE(Record):
    """
    Contains 2 bytes representing texttype. The value of the texttype must be in the range 0 to 63.
    """
    record_type = gdstypes.RecordType.TEXTTYPE
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    type: int

    @classmethod
    def read(cls, record: library.RawRecord) -> TEXTTYPE:
        super().read(record)
        self = cls.__new__(cls)
        self.type, = struct.unpack(">h", record.data)
        return self

    def __str__(self):
        return f"text type: {self.type}"

    def pack(self) -> bytes:
        return struct.pack(">h", self.type)


class PRESENTATION(Record):
    """
    Contains 1 word (2 bytes) of bit flags for text presentation. Bits 10 and 11, taken together as a binary number,
    specify the font (00 means font 0, 01 means font 1, 10 means font 2, and 11 means font 3). Bits 12 and 13 specify
    the vertical presentation (00 means top, 01 means middle, and 10 means bottom). Bits 14 and 15 specify the
    horizontal presentation (00 means left, 01 means center, and 10 means right). Bits 0 through 9 are reserved
    for future use and must be cleared. If this record is omitted, then top-left justification and font 0 are assumed.
    """
    record_type = gdstypes.RecordType.PRESENTATION
    data_type = gdstypes.DataType.BIT_ARRAY

    font: gdstypes.Font
    vertical_alignment: gdstypes.VerticalAlignment
    horizontal_alignment: gdstypes.HorizontalAlignment

    @classmethod
    def read(cls, record: library.RawRecord) -> PRESENTATION:
        super().read(record)
        self = cls.__new__(cls)
        data, = struct.unpack(">H", record.data)
        self.font = gdstypes.Font(data & (1 << 5) + data & (1 << 4))
        self.vertical_alignment = gdstypes.VerticalAlignment(data & (1 << 3) + data & (1 << 2))
        self.horizontal_alignment = gdstypes.HorizontalAlignment(data & (1 << 1) + data & (1 << 0))
        return self

    def __str__(self):
        return f"font: {str(self.font)}, vertical alignment: {str(self.vertical_alignment)}," \
               f" horizontal alignment: {str(self.horizontal_alignment)}"

    def pack(self) -> bytes:
        flags = self.horizontal_alignment.value + self.vertical_alignment.value + self.font.value
        return struct.pack(">H", flags)


class WIDTH(Record):
    """
    Contains four bytes which specify the width of a path or text lines in data base units. A negative
    value for width means that the width is absolute, i.e., it is not affected by the magnification
    factor of any parent reference. If omitted, zero is assumed.
    """
    record_type = gdstypes.RecordType.WIDTH
    data_type = gdstypes.DataType.FOUR_BYTE_SIGNED_INTEGER

    width: int

    def __init__(self, width: int):
        self.width = width

    @classmethod
    def read(cls, record: library.RawRecord) -> WIDTH:
        super().read(record)
        self = cls.__new__(cls)
        self.width, = struct.unpack(">i", record.data)
        return self

    def __str__(self):
        return f"width: {self.width}"

    def pack(self) -> bytes:
        return struct.pack(">i", self.width)


class STRANS(Record):
    """
    Contains two bytes of bit flags for SREF, AREF, and text transformation. Bit 0 (the leftmost bit)
    specifies reflection. If it is set, then reflection about the X-axis is applied before angular rotation.
    For AREFs, the entire array lattice is reflected, with the individual array elements rigidly attached.
    Bit 13 flags absolute magnification. Bit 14 flags absolute angle. Bit 15 (the rightmost bit) and all
    remaining bits are reserved for future use and must be cleared. If this record is omitted, then the element
    is assumed to have no reflection and its magnification and angle are assumed to be non-absolute.
    """
    record_type = gdstypes.RecordType.STRANS
    data_type = gdstypes.DataType.BIT_ARRAY

    reflect_about_x: bool
    absolute_magnification: bool
    absolute_angle: bool

    @classmethod
    def read(cls, record: library.RawRecord) -> STRANS:
        super().read(record)
        self = cls.__new__(cls)
        data, = struct.unpack(">H", record.data)
        self.reflect_about_x = bool(data & 1 << 14)
        self.absolute_magnification = bool(data & 1 << 1)
        self.absolute_angle = bool(data & 1 << 0)
        return self

    def __str__(self):
        return f"reflect about x: {self.reflect_about_x}, absolute magnification: {self.absolute_magnification}," \
               f" absolute angle: {self.absolute_angle}"

    def pack(self) -> bytes:
        flags = int(self.absolute_angle) + int(self.absolute_magnification) << 1 + int(self.reflect_about_x) << 14
        return struct.pack(">H", flags)


class STRING(Record):
    """
    Contains a character string for text presentation, up to 512 characters long.
    """
    record_type = gdstypes.RecordType.STRING
    data_type = gdstypes.DataType.ASCII_STRING

    text: str

    def __init__(self, text: str):
        self.text = text

    @classmethod
    def read(cls, record: library.RawRecord) -> STRING:
        super().read(record)
        self = cls.__new__(cls)
        self.text = record.data.decode(encoding = "ascii").rstrip("\0")
        return self

    def __str__(self):
        return f"String: {self.text}"

    def pack(self) -> bytes:
        return self.text.encode(encoding = "ascii") + b"\0"


class ENDSTR(SimpleRecord):
    """
    Marks the end of a structure
    """
    record_type = gdstypes.RecordType.ENDSTR


class ENDLIB(SimpleRecord):
    """
    Marks the end of a library.
    """
    record_type = gdstypes.RecordType.ENDLIB


class SREF(SimpleRecord):
    """
    Marks the beginning of an SREF (structure reference) element.
    """
    record_type = gdstypes.RecordType.SREF


class SNAME(Record):
    """
    Contains the name of a referenced structure. See also STRNAME.
    """
    record_type = gdstypes.RecordType.SNAME
    data_type = gdstypes.DataType.ASCII_STRING

    name: str

    def __init__(self, ref_name: str):
        self.name = ref_name


    @classmethod
    def read(cls, record: library.RawRecord) -> SNAME:
        super().read(record)
        self = cls.__new__(cls)
        self.name = record.data.decode(encoding = "ascii").rstrip("\0")
        return self

    def __str__(self):
        return f"reference name: {self.name}"

    def pack(self) -> bytes:
        return self.name.encode(encoding = "ascii") + b"\0"


class PROPATTR(Record):
    """
    Contains 2 bytes which specify the attribute number. The attribute number is an integer from 1 to
    127. Attribute numbers 126 and 127 are reserved for the user integer and user string (CSD) properties,
    which existed prior to Release 3.0.
    """
    record_type = gdstypes.RecordType.PROPATTR
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    property_number: int

    @classmethod
    def read(cls, record: library.RawRecord) -> PROPATTR:
        super().read(record)
        self = cls.__new__(cls)
        self.property_number, = struct.unpack(">h", record.data)
        return self

    def __str__(self):
        return f"property #{self.property_number}"

    def pack(self) -> bytes:
        return struct.pack(">h", self.property_number)


class PROPVALUE(Record):
    """
    Contains the string value associated with the attribute named in the preceding PROP ATTR record.
    Maximum length is 126 characters. The attributevalue pairs associated with anyone element must
    all have distinct attribute numbers. Also, there is a limit on the total amount of property data that
    may be associated with anyone element: the total length of all the strings, plus twice the number of
    attribute-value pairs, must not exceed 128 (or 512 if the element is an SREF, AREF, or node).
    """
    record_type = gdstypes.RecordType.PROPVALUE
    data_type = gdstypes.DataType.ASCII_STRING

    value: str

    @classmethod
    def read(cls, record: library.RawRecord) -> PROPVALUE:
        super().read(record)
        self = cls.__new__(cls)
        self.value = record.data.decode(encoding = "ascii").rstrip("\0")
        return self

    def __str__(self):
        return f"property value: {self.value}"

    def pack(self) -> bytes:
        return self.value.encode(encoding = "ascii") + b"\0"


class MAG(Record):
    """
    Contains a double-precision real number (8 bytes) which is the magnification factor.
    If omitted, a magnification of 1 is assumed.
    """
    record_type = gdstypes.RecordType.MAG
    data_type = gdstypes.DataType.EIGHT_BYTE_REAL

    magnification_factor: float

    def __init__(self, factor):
        self.magnification_factor = factor

    @classmethod
    def read(cls, record: library.RawRecord) -> MAG:
        super().read(record)
        self = cls.__new__(cls)
        self.magnification_factor = utils.eight_byte_real_to_float(record.data)
        return self

    def __str__(self):
        return f"magnification factor: {self.magnification_factor}"

    def pack(self) -> bytes:
        return utils.float_to_eight_byte_real(self.magnification_factor)


class ANGLE(Record):
    """
    Contains a double-precision real number (8 bytes) which is the angular rotation factor, measured in
    degrees and in counterclockwise direction. For an AREF, the ANGLE rotates the entire array lattice
    (with the individual array elements rigidlyattached) about the array reference point. If this record
    is omitted, an angle of zero degrees is assumed.
    """
    record_type = gdstypes.RecordType.ANGLE
    data_type = gdstypes.DataType.EIGHT_BYTE_REAL

    angular_rotation_factor: float

    def __init__(self, factor: float):
        self.angular_rotation_factor = factor

    @classmethod
    def read(cls, record: library.RawRecord) -> ANGLE:
        super().read(record)
        self = cls.__new__(cls)
        self.angular_rotation_factor = utils.eight_byte_real_to_float(record.data)
        return self

    def __str__(self):
        return f"angular rotation factor: {self.angular_rotation_factor}"

    def pack(self) -> bytes:
        return utils.float_to_eight_byte_real(self.angular_rotation_factor)


class RaithCircle(SimpleRecord):
    """
    Marks the beginning of an RAITHCIRCLE element.
    """
    record_type = gdstypes.RecordType.RAITHCIRCLE


class AREF(SimpleRecord):
    """
    Marks the beginning of an AREF (array reference) element.
    """
    record_type = gdstypes.RecordType.AREF


class COLROW(Record):
    """
    Contains 4 bytes. The first 2 bytes contain the number of columns in the array. The third and fourth
    bytes contain the number of rows. Neither the number of columns nor the number of rows may exceed
    32,767 (decimal), and both are positive.
    """
    record_type = gdstypes.RecordType.COLROW
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    n_cols: int
    n_rows: int

    def __init__(self, n_rows: int, n_cols: int):
        self.n_rows = n_rows
        self.n_cols = n_cols

    @classmethod
    def read(cls, record: library.RawRecord) -> COLROW:
        super().read(record)
        self = cls.__new__(cls)
        self.n_cols, self.n_rows = struct.unpack(">hh", record.data)
        return self

    def __str__(self):
        return f"number of columns: {self.n_cols}, number of rows: {self.n_rows}"

    def pack(self) -> bytes:
        return struct.pack(">hh", self.n_cols, self.n_rows)


class PATH(SimpleRecord):
    """
    Marks the beginning of a path element.
    """
    record_type = gdstypes.RecordType.PATH


class NODE(SimpleRecord):
    """
    Marks the beginning of a node.
    """
    record_type = gdstypes.RecordType.NODE


class NODETYPE(Record):
    """
    Contains 2 bytes which specify nodetype. The value of the nodetype must be in the range of 0 to 63.
    """
    record_type = gdstypes.RecordType.NODETYPE
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    type: int

    def __init__(self, type: int):
        self.type = type

    @classmethod
    def read(cls, record: library.RawRecord) -> NODETYPE:
        super().read(record)
        self = cls.__new__(cls)
        self.type, = struct.unpack(">h", record.data)
        return self

    def pack(self) -> bytes:
        return struct.pack(">h", self.type)


class ELFLAGS(Record):
    """
    Contains 2 bytes of bit flags. Bit 15 (the rightmost bit) specifies Template data. Bit 14 specifies
    External data (also referred to as Exterior data). All other bits are currently unused and must be
    cleared to o. If this record is omitted, then all bits are assumed to be o
    """
    record_type = gdstypes.RecordType.ELFLAGS
    data_type = gdstypes.DataType.BIT_ARRAY

    template_data: bool
    external_data: bool

    @classmethod
    def read(cls, record: library.RawRecord) -> ELFLAGS:
        super().read(record)
        self = cls.__new__(cls)
        data, = struct.unpack(">H", record.data)
        self.template_data = bool(data & 1 << 0)
        self.external_data = bool(data & 1 << 1)
        return self

    def pack(self) -> bytes:
        flags = self.template_data + self.external_data << 1
        return struct.pack(">H", flags)


class PLEX(Record):
    """
    A unique positive number which is common to all elements of the plex to which this element belongs.
    The head of the plex is flagged by setting the seventh bit; therefore, plex numbers should be small
    enough to occupy only the rightmost 24 bits. If this record is omitted, then the element is not a
    plex member.
    """
    record_type = gdstypes.RecordType.PLEX
    data_type = gdstypes.DataType.FOUR_BYTE_SIGNED_INTEGER

    number: int

    @classmethod
    def read(cls, record: library.RawRecord) -> PLEX:
        super().read(record)
        self = cls.__new__(cls)
        self.number, = struct.unpack(">i", record.data)
        return self

    def pack(self) -> bytes:
        return struct.pack(">i", self.number)


class PATHTYPE(Record):
    """
    This record contains a value of 0 for square-ended paths that end flush with their endpoints, 1 for
    round-ended paths, and 2 for square-ended paths that extend a half-width beyond their endpoints.
    If not specified, a Pathtype of 0 is assumed.
    """
    record_type = gdstypes.RecordType.PATHTYPE
    data_type = gdstypes.DataType.TWO_BYTE_SIGNED_INTEGER

    type: int

    def __init__(self, path_type: int):
        self.type = path_type

    @classmethod
    def read(cls, record: library.RawRecord) -> PATHTYPE:
        super().read(record)
        self = cls.__new__(cls)
        self.type, = struct.unpack(">h", record.data)
        return self

    def pack(self) -> bytes:
        return struct.pack(">h", self.type)
