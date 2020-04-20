from __future__ import annotations
import typing

if typing.TYPE_CHECKING:
    import libgdsii.gdstypes as gdstypes


class UnknownRecordException(Exception):
    def __init__(self, type: int):
        super().__init__()
        self.type = type

    def __str__(self):
        return f"Unknown record found. Found: 0x{self.type:02x}"


class UnknownDatatypeWarning(Warning):
    def __init__(self, type: int):
        super().__init__()
        self.type = type

    def __str__(self):
        return f"Unknown datatype found. Found: {self.type}"


class UnexpectedRecordException(Exception):
    def __init__(self, expected_type: gdstypes.RecordType, actual_type: gdstypes.RecordType):
        super().__init__()
        self._expected = expected_type
        self._actual = actual_type

    def __str__(self):
        return f"Found unexpected record. Expected: {self._expected}, got {self._actual}"


class DatatypeMismatchWarning(Warning):
    def __init__(self, expected_type: gdstypes.DataType, actual_type: gdstypes.DataType):
        super().__init__()
        self._expected = expected_type
        self._actual = actual_type

    def __str__(self):
        return f"Found non matching datatypes. Expected: {str(self._expected)}, got {str(self._actual)}"


class MissingRecordException(Exception):
    def __init__(self, expected_type: gdstypes.RecordType, actual_type: gdstypes.RecordType):
        super().__init__()
        self.expected_type = expected_type
        self.actual_type = actual_type

    def __str__(self):
        return f"{str(self.expected_type)} is missing, found {str(self.actual_type)}"


class UnsupportedRecordWarning(Warning):
    def __init__(self, type: gdstypes.RecordType):
        super().__init__()
        self.type = type

    def __str__(self):
        return f"Unsupported record found: Found: {str(self.type)}"
