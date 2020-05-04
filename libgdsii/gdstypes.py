from __future__ import annotations

import enum
import warnings
import libgdsii.exceptions as exceptions


@enum.unique
class RecordType(enum.IntEnum):
    HEADER = 0x00  # Contains two bytes of data representing the version number.
    BGNLIB = 0x01  # Contains last modification time of library
    LIBNAME = 0x02  # Contains a string which is the library name
    UNITS = 0x03  # Contains 2 8-byte real numbers. The first is the size of a database unit in user units. The second is the size of a database unit in meters.
    ENDLIB = 0x04  # Marks the end of a library.
    BGNSTR = 0x05  # Contains creation time and last modification time of a structure (in the same format as for the BGNLIB record) and marks the beginning of a structure.
    STRNAME = 0x06  # Contains a string which is the structure name.
    ENDSTR = 0x07  # Marks the end of a structure.
    BOUNDARY = 0x08  # Marks the beginning of a boundary element.
    PATH = 0x09  # Marks the beginning of a path element.
    SREF = 0x0A  # Marks the beginning of an SREF (structure reference) element.
    AREF = 0x0B  # Marks the beginning of an AREF (array reference) element.
    TEXT = 0x0C  # Marks the beginning of a text element.
    LAYER = 0x0D  # Contains 2 bytes which specify the layer.
    DATATYPE = 0x0E  # Contains 2 bytes which specify data type
    WIDTH = 0x0F  # Contains four bytes which specify the width of a path or text lines in data base units.
    XY = 0x10  # Contains an array of XY coordinates in database units. Each X or Y coordinate is four bytes long
    ENDEL = 0x11  # Marks the end of an element.
    SNAME = 0x12  # Contains the name of a referenced structure.
    COLROW = 0x13  # Contains 4 bytes. The first 2 bytes contain the number of columns in the array. The third and fourth bytes contain the number of rows
    TEXTNODE = 0x14  # Marks the beginning of a text node. (Unused)
    NODE = 0x15  # Marks the beginning of a node.
    TEXTTYPE = 0x16  # Contains 2 bytes representing text type.
    PRESENTATION = 0x17  # Contains 2 bytes of bit flags for text presentation.
    SPACING = 0x18  # Discontinued
    STRING = 0x19  # Contains a character string for text presentation
    STRANS = 0x1A  # Contains two bytes of bit flags for SREF, AREF, and text transformation
    MAG = 0x1B  # Contains a double-precision real number (8 bytes) which is the magnification factor
    ANGLE = 0x1C  # Contains a double-precision real number (8 bytes) which is the angular rotation factor, measured in degrees and in counterclockwise direction.
    UINTEGER = 0x1D  # No longer used
    USTRING = 0x1E  # No longer used
    REFLIBS = 0x1F  # Contains the names of the reference libraries.
    FONTS = 0x20  # Contains names of textfont definition files.
    PATHTYPE = 0x21  # This record contains a value of 0 for square-ended paths that end flush with their endpoints, 1 for round-ended paths, and 2 for square-ended paths that extend a half-width beyond their endpoints.
    GENERATIONS = 0x22  # This record contains a positive count of the number of copies of deleted or backed-up structures to retain
    ATTRTABLE = 0x23  # Contains the name of the attribute definition file.
    STYPTABLE = 0x24  # Unreleased feature
    STRTYPE = 0x25  # Unreleased feature
    ELFLAGS = 0x26  # Contains 2 bytes of bit flags. Bit 15 (the rightmost bit) specifies Template data. Bit 14 specifies External data
    ELKEY = 0x27  # Unreleased feature
    LINKTYPE = 0x28  # Unreleased feature
    LINKKEYS = 0x29  # Unreleased feature
    NODETYPE = 0x2A  # Contains 2 bytes which specify nodetype.
    PROPATTR = 0x2B  # Contains 2 bytes which specify the attribute number.
    PROPVALUE = 0x2C  # Contains the string value associated with the attribute named in the preceding PROPATTR record
    BOX = 0x2D  # Marks the beginning of a box element
    BOXTYPE = 0x2E  # Contains 2 bytes which specify box type.
    PLEX = 0x2F  # A unique positive number which is common to all elements of the plex to which this element belongs.
    BGNEXTN = 0x30  # This record type only occurs in CustomPlus.
    ENDEXTN = 0x31  # This record type only occurs in CustomPlus.
    TAPENUM = 0x32  # Contains two bytes which specify the number of the current reel of tape for a multi-reel Stream file
    TAPECODE = 0x33  # Contains 12 bytes. This is a unique 6-integer code which is common to all the reels of a multi-reel Stream file.
    STRCLASS = 0x34  # This record type only occurs in CustomPlus.
    RESERVED = 0x35  # Reserved for future use.
    FORMAT = 0x36  # Defines the format type of a Stream tape in two bytes. The two possible values are: 0 for Archive format, 1 for Filtered format.
    MASK = 0x37  # Required for Filtered format, and present only in Filtered Stream file
    ENDMASKS = 0x38  # Required for Filtered format, and present only in Filtered Stream file
    LIBDIRSIZE = 0x39  # Contains the number of pages in the Library directory
    SRFNAME = 0x3A  # Contains the name of the Sticks Rules File, if one is bound to th-e library
    LIBSECUR = 0x3B  # Contains an array of Access Control List (ACL) data

    # RAITH types
    RAITHCIRCLE = 0x56  # Marks the beginning of a Raith circle element

    @classmethod
    def _missing_(cls, value):
        raise exceptions.UnknownRecordException(value)


@enum.unique
class DataType(enum.IntEnum):
    NO_DATA_PRESENT = 0
    BIT_ARRAY = 1
    TWO_BYTE_SIGNED_INTEGER = 2
    FOUR_BYTE_SIGNED_INTEGER = 3
    FOUR_BYTE_REAL = 4  # (Unused)
    EIGHT_BYTE_REAL = 5
    ASCII_STRING = 6
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, value):
        warnings.warn(exceptions.UnknownDatatypeWarning(value))
        return cls._create_pseudo_member_(value)

    @classmethod
    def _create_pseudo_member_(cls, value):
        pseudo_member = cls._value2member_map_.get(value, None)
        if pseudo_member is None:
            new_member = int.__new__(cls, value)
            # I expect a name attribute to hold a string, hence str(value)
            # However, new_member._name_ = value works, too
            new_member._name_ = str(value)
            new_member._value_ = value
            pseudo_member = cls._value2member_map_.setdefault(value, new_member)
        return pseudo_member


@enum.unique
class Font(enum.IntEnum):
    """
    Bits 10 and 11, taken together as a binary number, specify the font
    """
    FONT0 = 0b0000_0000
    FONT1 = 0b0001_0000
    FONT2 = 0b0010_0000
    FONT3 = 0b0011_0000


@enum.unique
class VerticalAlignment(enum.IntEnum):
    """
    Bits 12 and 13 specify the vertical presentation
    """
    TOP = 0b0000_0000
    MIDDLE = 0b0000_0100
    BOTTOM = 0b0000_1000


@enum.unique
class HorizontalAlignment(enum.IntEnum):
    """
    Bits 14 and 15 specify the horizontal presentation
    """
    LEFT = 0b0000_00000
    CENTER = 0b0000_0001
    RIGHT = 0b0000_0010


@enum.unique
class Version(enum.Enum):
    LESS_THAN_THREE = 0
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 600
    SEVEN = 7

@enum.unique
class PathType(enum.Enum):
    BUTT = 0
    ROUND = 1
    SQUARE = 2
