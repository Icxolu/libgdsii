from __future__ import annotations
import typing

import struct
import io
import collections
import warnings
import numpy as np

import libgdsii.gdstypes as gdstypes
import libgdsii.records as records
import libgdsii.exceptions as exceptions
import libgdsii.utils as utils


class Library(collections.OrderedDict):
    """
    Dictionary of structures indexed by structure name, along with metadata

    HEADER BGNLIB [LIBDIRSIZE] [SRFNAME] [LIBSECUR] LIBNAME [REFLIBS] [FONTS] [ATTRTABLE] [GENERATIONS] [<FormatType>] UNITS {<structure>}* ENDLIB
    """

    _HEADER: records.HEADER
    _BGNLIB: records.BGNLIB
    _LIBNAME: records.LIBNAME
    _UNITS: records.UNITS
    _ENDLIB: records.ENDLIB

    _LIBDIRSIZE = None
    _SRFNAME = None
    _LIBSECUR = None
    _REFLIBS = None
    _FONTS = None
    _ATTRTABLE = None
    _GENERATIONS = None
    _FormatType = None

    def __init__(self,
                 name: str,
                 logical_unit: float = 0.001,
                 physical_unit: float = 1e-9,
                 version: gdstypes.Version = gdstypes.Version.SEVEN,
                 mod_date: utils.DateTime = utils.DateTime.utcnow(),
                 acc_date: utils.DateTime = utils.DateTime.utcnow()
                 ):
        super().__init__()
        self._HEADER = records.HEADER(version)
        self._BGNLIB = records.BGNLIB(mod_date, acc_date)
        self._LIBNAME = records.LIBNAME(name)
        self._UNITS = records.UNITS(logical_unit, physical_unit)
        self._ENDLIB = records.ENDLIB()

    @property
    def version(self):
        return self._HEADER.version

    @version.setter
    def version(self, version: gdstypes.Version):
        self._HEADER.version = version

    @property
    def name(self):
        return self._LIBNAME.name

    @property
    def modification_date(self):
        return self._BGNLIB.modification_date

    @modification_date.setter
    def modification_date(self, date: utils.DateTime):
        self._BGNLIB.modification_date = date

    @property
    def access_date(self):
        return self._BGNLIB.access_date

    @access_date.setter
    def access_date(self, date: utils.DateTime):
        self._BGNLIB.access_date = date

    @name.setter
    def name(self, name: str):
        self._LIBNAME.name = name

    @property
    def logical_unit(self):
        return self._UNITS.logical_unit

    @logical_unit.setter
    def logical_unit(self, value):
        self._UNITS.logical_unit = value

    @property
    def physical_unit(self):
        return self._UNITS.physical_unit

    @physical_unit.setter
    def physical_unit(self, value):
        self._UNITS.physical_unit = value

    @classmethod
    def load_from_file(cls, stream: typing.BinaryIO) -> Library:
        self = cls.__new__(cls)
        collections.OrderedDict.__init__(self)

        reader = Reader(stream)

        # read header (required)
        self._HEADER = records.HEADER.read(reader.read_next())
        # read begin of library (required)
        self._BGNLIB = records.BGNLIB.read(reader.read_next())

        # read optional records
        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.LIBDIRSIZE:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.SRFNAME:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.LIBSECUR:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        # read library name (required)
        self._LIBNAME = records.LIBNAME.read(record)

        # read optional records
        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.REFLIBS:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.FONTS:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.ATTRTABLE:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.GENERATIONS:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.FORMAT:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        # read units (required)
        self._UNITS = records.UNITS.read(record)

        for record in reader:
            if record.record_type is gdstypes.RecordType.BGNSTR:
                structure = Structure.read(reader)
                self[structure.name] = structure
            elif record.record_type is gdstypes.RecordType.ENDLIB:
                self._ENDLIB = records.ENDLIB.read(record)
                break
            else:
                raise exceptions.MissingRecordException(gdstypes.RecordType.ENDLIB, record.record_type)

        return self

    def write(self, stream: typing.BinaryIO):
        self._HEADER.write(stream)
        self._BGNLIB.write(stream)
        self._LIBDIRSIZE.write(stream) if self._LIBDIRSIZE is not None else None
        self._SRFNAME.write(stream) if self._SRFNAME is not None else None
        self._LIBSECUR.write(stream) if self._LIBSECUR is not None else None
        self._LIBNAME.write(stream)
        self._REFLIBS.write(stream) if self._REFLIBS is not None else None
        self._FONTS.write(stream) if self._FONTS is not None else None
        self._ATTRTABLE.write(stream) if self._ATTRTABLE is not None else None
        self._GENERATIONS.write(stream) if self._GENERATIONS is not None else None
        self._FormatType.write(stream) if self._FormatType is not None else None
        self._UNITS.write(stream)

        structure: Structure
        for structure in self.values():
            structure.write(stream)

        self._ENDLIB.write(stream)

    @property
    def layers(self):
        return sorted(set(
                [element.layer for structure in self.values() for element in structure if hasattr(element, "layer")]
        ))

    def draw(self, fobj: typing.BinaryIO, scale = 1, options = { }):
        import cairo

        options["scale"] = scale

        layers: typing.DefaultDict[int, cairo.RecordingSurface] = collections.defaultdict(
                lambda: cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None))

        for sname in options.get("structures", self.keys()):
            structure = self[sname]
            layers = structure._draw(self, layers, options)

        # for some reason we cant paint these recording surfaces onto another recording surface to
        # determine the bounds of the whole picture, so we need to do this manually

        draw_surfs = [layers[i] for i in options.get("order", self.layers)]
        if len(draw_surfs) == 0: return

        dims = np.array([surf.ink_extents() for surf in draw_surfs])
        dims[:, 2:] += dims[:, :2]
        x0, y0 = np.min(dims[:, :2], axis = 0)
        x1, y1 = np.max(dims[:, 2:], axis = 0)
        w, h = x1 - x0, y1 - y0

        scale = 1
        with cairo.PDFSurface(fobj, scale * w, scale * h) as surf:
            ctx = cairo.Context(surf)
            ctx.translate(0, scale * h)
            ctx.scale(scale, -scale)

            for layer_surf in draw_surfs:
                ctx.set_source_surface(layer_surf, -x0, -y0)
                ctx.paint()


class Structure(list):
    """
    List of elements inside the structure along with metadata

    BGNSTR STRNAME [STRCLASS] {<element>}* ENDSTR
    """
    _BGNSTR: records.BGNSTR
    _STRNAME: records.STRNAME
    _ENDSTR: records.ENDSTR

    _STRCLASS: records.Record = None

    def __init__(self,
                 name: str,
                 mod_date: utils.DateTime = utils.DateTime.utcnow(),
                 acc_date: utils.DateTime = utils.DateTime.utcnow()
                 ):
        super().__init__()
        self._BGNSTR = records.BGNSTR(mod_date, acc_date)
        self._STRNAME = records.STRNAME(name)
        self._ENDSTR = records.ENDSTR()

    @property
    def modification_date(self):
        return self._BGNSTR.modification_date

    @modification_date.setter
    def modification_date(self, date: utils.DateTime):
        self._BGNSTR.modification_date = date

    @property
    def access_date(self):
        return self._BGNSTR.access_date

    @access_date.setter
    def access_date(self, date: utils.DateTime):
        self._BGNSTR.access_date = date

    @property
    def name(self):
        return self._STRNAME.name

    @name.setter
    def name(self, name):
        self._STRNAME.name = name

    @classmethod
    def read(cls, reader: Reader) -> Structure:
        self = cls.__new__(cls)
        list.__init__(self)

        # read begin structure (required)
        self._BGNSTR = records.BGNSTR.read(reader.current)
        # read structure name (required)
        self._STRNAME = records.STRNAME.read(reader.read_next())

        # read optional records
        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.STRCLASS:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            reader.read_next()

        reader.revert()

        for record in reader:
            if reader.current.record_type is gdstypes.RecordType.BOUNDARY:
                self.append(BoundaryElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.PATH:
                self.append(PathElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.SREF:
                self.append(StructureReferenceElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.AREF:
                self.append(ArrayReferenceElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.TEXT:
                self.append(TextElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.NODE:
                self.append(NodeElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.BOX:
                self.append(BoxElement.read(reader))
            elif reader.current.record_type is gdstypes.RecordType.RAITHCIRCLE:
                self.append(RaithCircleElement.read(reader))
            elif record.record_type is gdstypes.RecordType.ENDSTR:
                self._ENDSTR = records.ENDSTR.read(record)
                break
            else:
                raise exceptions.MissingRecordException(gdstypes.RecordType.ENDSTR, record.record_type)

        return self

    def write(self, stream: typing.BinaryIO):
        self._BGNSTR.write(stream)
        self._STRNAME.write(stream)
        self._STRCLASS.write(stream) if self._STRCLASS is not None else None

        element: Element
        for element in self:
            element.write(stream)

        self._ENDSTR.write(stream)

    def _draw(self, lib, layers, options):
        for element in self:
            layers = element._draw(lib, layers, options)

        return layers


class Element(list):
    """
    Base clase for all elements. List of properties of the specific element

    {<boundary> | <path> | <SREF> | <AREF> | <text> | <node> | <box>} {<property>}* ENDEL
    """
    _ENDEL: records.ENDEL

    @classmethod
    def read(cls, reader: Reader) -> Element:
        raise NotImplementedError()

    def _read_properties(self: Element, reader: Reader):
        for record in reader:
            if record.record_type is gdstypes.RecordType.PROPATTR:
                self.append(records.PROPATTR.read(record))
                self.append(records.PROPVALUE.read(reader.read_next()))
            elif record.record_type is gdstypes.RecordType.ENDEL:
                self._ENDEL = records.ENDEL.read(record)
                break
            else:
                raise exceptions.MissingRecordException(gdstypes.RecordType.ENDEL, record.record_type)

    def write(self, stream: typing.BinaryIO):
        prop: records.Record
        for prop in self:
            prop.write(stream)

        self._ENDEL.write(stream)


    def _draw(self, lib, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        raise NotImplementedError()


class BoundaryElement(Element):
    """
    BOUNDARY [ELFLAGS] [PLEX] LAYER DATATYPE XY {<property>}* ENDEL
    """
    _BOUNDARY: records.BOUNDARY
    _LAYER: records.LAYER
    _DATATYPE: records.DATATYPE
    _XY: records.XY

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None

    def __init__(self,
                 layer: int,
                 xy: np.ndarray[int],
                 data_type: gdstypes.DataType = gdstypes.DataType.NO_DATA_PRESENT):
        super().__init__()

        self._BOUNDARY = records.BOUNDARY()
        self._LAYER = records.LAYER(layer)
        self._DATATYPE = records.DATATYPE(data_type)
        self._XY = records.XY()
        self.coordinates = xy
        self._ENDEL = records.ENDEL()

    @property
    def layer(self):
        return self._LAYER.layer

    @layer.setter
    def layer(self, layer: int):
        self._LAYER.layer = layer

    @property
    def datatype(self):
        return self._DATATYPE.data_type

    @datatype.setter
    def datatype(self, datatype: gdstypes.DataType):
        self._DATATYPE.data_type = datatype

    @property
    def coordinates(self):
        return self._XY.x.copy(), self._XY.y.copy()

    @coordinates.setter
    def coordinates(self, xy: np.ndarray[int]):
        if xy.shape[0] < 4 or xy.shape[1] != 2 or xy[0, :] != xy[-1, :]: raise RuntimeError()
        self._XY.x = xy[:, 0].copy()
        self._XY.y = xy[:, 1].copy()

    @classmethod
    def read(cls, reader: Reader) -> BoundaryElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._BOUNDARY = records.BOUNDARY.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._LAYER = records.LAYER.read(record)
        self._DATATYPE = records.DATATYPE.read(reader.read_next())
        self._XY = records.XY.read(reader.read_next())
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._BOUNDARY.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._LAYER.write(stream)
        self._DATATYPE.write(stream)
        self._XY.write(stream)
        super().write(stream)

    def _draw(self, lib: Library, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        import cairo
        scale = options["scale"]

        X, Y = self.coordinates
        X = X * lib.logical_unit * scale
        Y = Y * lib.logical_unit * scale

        surf = layers[self.layer]
        ctx = cairo.Context(surf)
        ctx.save()
        ctx = utils._parse_line_width(options, ctx, self.layer)

        ctx.translate(*shift)
        ctx.move_to(X[0], Y[0])
        for x, y in zip(X[1:], Y[1:]):
            ctx.line_to(x, y)

        ctx.close_path()
        ctx = utils._parse_fill_color(options, ctx, self.layer)
        ctx = utils._parse_pattern(options, ctx, self.layer)
        ctx.fill_preserve()

        ctx = utils._parse_stroke_color(options, ctx, self.layer)
        ctx.stroke()

        ctx.restore()
        return layers


class PathElement(Element):
    """
    PATH [ELFLAGS] [PLEX] LAYER DATATYPE [PATHTYPE] [WIDTH] [BGNEXTN] [ENDEXTN] XY {<property>}* ENDEL
    """

    _PATH: records.PATH
    _LAYER: records.LAYER
    _DATATYPE: records.DATATYPE
    _XY: records.XY

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None
    _PATHTYPE: records.PATHTYPE = None
    _WIDTH: records.WIDTH = None
    _BGNEXTN: records.Record = None
    _ENDEXTN: records.Record = None

    def __init__(self,
                 layer: int,
                 xy: np.ndarray[int],
                 width: int = 0,
                 pathtype: gdstypes.PathType = gdstypes.PathType.BUTT,
                 datatype: gdstypes.DataType = gdstypes.DataType.NO_DATA_PRESENT):
        super().__init__()

        self._PATH = records.PATH()
        self._LAYER = records.LAYER(layer)
        self._XY = records.XY()
        self.coordinates = xy
        if width != 0: self._WIDTH = records.WIDTH(width)
        if pathtype != gdstypes.PathType.BUTT: self._PATHTYPE = records.PATHTYPE(pathtype)
        self._DATATYPE = records.DATATYPE(datatype)
        self._ENDEL = records.ENDEL()

    @property
    def layer(self):
        return self._LAYER.layer

    @layer.setter
    def layer(self, layer: int):
        self._LAYER.layer = layer

    @property
    def datatype(self):
        return self._DATATYPE.data_type

    @datatype.setter
    def datatype(self, datatype: gdstypes.DataType):
        self._DATATYPE.data_type = datatype

    @property
    def coordinates(self):
        return self._XY.x.copy(), self._XY.y.copy()

    @coordinates.setter
    def coordinates(self, xy: np.ndarray[int]):
        if xy.shape[0] < 2 or xy.shape[1] != 2: raise RuntimeError()
        self._XY.x = xy[:, 0].copy()
        self._XY.y = xy[:, 1].copy()

    @property
    def pathtype(self):
        try:
            return self._PATHTYPE.type
        except AttributeError:
            return gdstypes.PathType.BUTT

    @pathtype.setter
    def pathtype(self, path_type: gdstypes.PathType):
        try:
            self._PATHTYPE.type = path_type
        except AttributeError:
            self._PATHTYPE = records.PATHTYPE(path_type)

    @property
    def width(self):
        try:
            return self._WIDTH.width
        except AttributeError:
            return 0

    @width.setter
    def width(self, width: int):
        if width == 0: return
        try:
            self._WIDTH.width = width
        except AttributeError:
            self._WIDTH = records.WIDTH(width)

    @classmethod
    def read(cls, reader: Reader) -> PathElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._PATH = records.PATH.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._LAYER = records.LAYER.read(record)
        self._DATATYPE = records.DATATYPE.read(reader.read_next())

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.PATHTYPE:
            self._PATHTYPE = records.PATHTYPE.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.WIDTH:
            self._WIDTH = records.WIDTH.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.BGNEXTN:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.ENDEXTN:
            warnings.warn(exceptions.UnsupportedRecordWarning(record.record_type))
            record = reader.read_next()

        self._XY = records.XY.read(record)
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._PATH.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._LAYER.write(stream)
        self._DATATYPE.write(stream)
        self._PATHTYPE.write(stream) if self._PATHTYPE is not None else None
        self._WIDTH.write(stream) if self._WIDTH is not None else None
        self._BGNEXTN.write(stream) if self._BGNEXTN is not None else None
        self._ENDEXTN.write(stream) if self._ENDEXTN is not None else None
        self._XY.write(stream)
        super().write(stream)

    def _draw(self, lib, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        import cairo
        scale = options["scale"]

        X, Y = self.coordinates
        X = X * lib.logical_unit * scale
        Y = Y * lib.logical_unit * scale

        surf = layers[self.layer]
        ctx = cairo.Context(surf)
        ctx.save()
        ctx.set_line_width(self.width * lib.logical_unit * scale)

        ctx.translate(*shift)
        ctx.move_to(X[0], Y[0])
        for x, y in zip(X[1:], Y[1:]):
            ctx.line_to(x, y)

        if self.pathtype == gdstypes.PathType.BUTT:
            ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        elif self.pathtype == gdstypes.PathType.ROUND:
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        elif self.pathtype == gdstypes.PathType.SQUARE:
            ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

        ctx = utils._parse_stroke_color(options, ctx, self.layer)
        ctx.stroke()

        ctx.restore()
        return layers


class RaithCircleElement(Element):
    """
    PATH LAYER DATATYPE [WIDTH] XY {<property>}* ENDEL
    """
    _RAITHCIRCLE: records.RaithCircle
    _LAYER: records.LAYER
    _DATATYPE: records.DATATYPE
    _XY: records.XY

    _WIDTH: records.WIDTH = None

    def __init__(self,
                 layer: int,
                 radii: typing.Tuple[int, int],
                 center: typing.Tuple[int, int],
                 width: int = 0,
                 datatype: gdstypes.DataType = gdstypes.DataType.NO_DATA_PRESENT):
        super().__init__()
        self._RAITHCIRCLE = records.RaithCircle()
        self._LAYER = records.LAYER(layer)
        self._XY = records.XY()
        self.radii = radii
        self.center = center
        if width != 0: self._WIDTH = records.WIDTH(width)
        self._DATATYPE = records.DATATYPE(datatype)
        self._ENDEL = records.ENDEL()

    @property
    def layer(self):
        return self._LAYER.layer

    @layer.setter
    def layer(self, layer: int):
        self._LAYER.layer = layer

    @property
    def datatype(self):
        return self._DATATYPE.data_type

    @datatype.setter
    def datatype(self, datatype: gdstypes.DataType):
        self._DATATYPE.data_type = datatype

    @property
    def width(self):
        try:
            return self._WIDTH.width
        except AttributeError:
            return 0

    @width.setter
    def width(self, width: int):
        try:
            self._WIDTH.width = width
        except AttributeError:
            self._WIDTH = records.WIDTH(width)

    @property
    def center(self):
        return self._XY.x[0], self._XY.y[0]

    @center.setter
    def center(self, value: typing.Tuple[int, int]):
        x, y = value
        self._XY.x[0] = x
        self._XY.y[0] = y

    @property
    def radii(self):
        return self._XY.x[1], self._XY.y[1]

    @radii.setter
    def radii(self, value: typing.Tuple[int, int]):
        x, y = value
        self._XY.x[1] = x
        self._XY.y[1] = y

    @property
    def arc(self):
        return self._XY.x[2], self._XY.y[2]

    @arc.setter
    def arc(self, value: typing.Tuple[int, int]):
        x, y = value
        self._XY.x[2] = x
        self._XY.y[2] = y

    @property
    def is_ellipse(self):
        return bool(self._XY.y[3] & 1 << 0)

    @property
    def is_filled(self):
        return bool(self._XY.y[3] & 1 << 1)

    @property
    def is_arc(self):
        return bool(self._XY.y[3] & 1 << 2)

    @classmethod
    def read(cls, reader: Reader) -> RaithCircleElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._RAITHCIRCLE = records.RaithCircle.read(reader.current)

        # record = reader.read_next()
        # if record.record_type is Types.RecordType.ELFLAGS:
        #     self._ELFLAGS = records.ElementFlags.read(record)
        #     record = reader.read_next()
        #
        # if record.record_type is Types.RecordType.PLEX:
        #     self._PLEX = records.Plex.read(record)
        #     record = reader.read_next()

        self._LAYER = records.LAYER.read(reader.read_next())
        self._DATATYPE = records.DATATYPE.read(reader.read_next())

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.WIDTH:
            self._WIDTH = records.WIDTH.read(record)
            record = reader.read_next()

        self._XY = records.XY.read(record)
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._RAITHCIRCLE.write(stream)
        # self._ELFLAGS.write() if self._ELFLAGS is not None else None
        # self._PLEX.write() if self._PLEX is not None else None
        self._LAYER.write(stream)
        self._DATATYPE.write(stream)
        self._WIDTH.write(stream) if self._WIDTH is not None else None
        self._XY.write(stream)
        super().write(stream)

    def _draw(self, lib: Library, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        import cairo
        scale = options["scale"]

        x, y = self.center
        x *= lib.logical_unit * scale
        y *= lib.logical_unit * scale

        x += shift[0]
        y += shift[1]

        surf = layers[self.layer]
        ctx = cairo.Context(surf)
        ctx.save()
        ctx.translate(*shift)
        ctx = utils._parse_line_width(options, ctx, self.layer)

        if not (self.is_ellipse or self.is_arc):
            ctx.arc(x, y, self.radii[0] * lib.logical_unit * scale, 0, 2 * np.pi)

        if self.is_filled:
            ctx = utils._parse_fill_color(options, ctx, self.layer)
            ctx = utils._parse_pattern(options, ctx, self.layer)
            ctx.fill_preserve()

        ctx = utils._parse_stroke_color(options, ctx, self.layer)
        ctx.stroke()

        ctx.restore()
        return layers


class StructureReferenceElement(Element):
    """
    SREF [ELFLAGS] [PLEX] SNAME [<strans>] XY {<property>}* ENDEL
    """

    _SREF: records.SREF
    _SNAME: records.SNAME
    _XY: records.XY

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None
    _TRANSFORMATION: StructureTransformationElement = None

    def __init__(self,
                 refname: str,
                 xy: typing.Tuple[int, int]):
        super().__init__()
        self._SREF = records.SREF()
        self._SNAME = records.SNAME(refname)
        self._XY = records.XY()
        self.coordinates = xy

    @property
    def ref_name(self):
        return self._SNAME.name

    @ref_name.setter
    def ref_name(self, ref_name: str):
        self._SNAME.name = ref_name

    @property
    def coordinates(self):
        return self._XY.x[0], self._XY.y[0]

    @coordinates.setter
    def coordinates(self, value: typing.Tuple[int, int]):
        x, y = value
        self._XY.x = [x]
        self._XY.y = [y]

    @classmethod
    def read(cls, reader: Reader) -> StructureReferenceElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._SREF = records.SREF.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._SNAME = records.SNAME.read(record)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.STRANS:
            self._TRANSFORMATION = StructureTransformationElement.read(reader)

        self._XY = records.XY.read(reader.current)
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._SREF.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._SNAME.write(stream)
        self._TRANSFORMATION.write(stream) if self._TRANSFORMATION is not None else None
        self._XY.write(stream)
        super().write(stream)

    def _draw(self, lib, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        scale = options["scale"]
        x, y = self.coordinates
        x = x * lib.logical_unit * scale
        y = y * lib.logical_unit * scale

        x += shift[0]
        y += shift[1]
        structure = lib[self.ref_name]
        for element in structure:
            layers = element._draw(lib, layers, options, (x, y))

        return layers


class ArrayReferenceElement(Element):
    """
    AREF [ELFLAGS] [PLEX] SNAME [<strans>] COLROW XY {<property>}* ENDEL
    """

    _AREF: records.AREF
    _SNAME: records.SNAME
    _COLROW: records.COLROW
    _XY: records.XY

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None
    _TRANSFORMATION: StructureTransformationElement = None

    def __init__(self,
                 refname: str,
                 reference_point: typing.Tuple[int, int],
                 dimensions: typing.Tuple[int, int],
                 row_spacing: typing.Tuple[int, int],
                 col_spacing: typing.Tuple[int, int]):
        super().__init__()
        self._AREF = records.AREF()
        self._SNAME = records.SNAME(refname)
        self._COLROW = records.COLROW(*dimensions)
        self._XY = records.XY()
        self.coordinates = np.c_[reference_point, np.array(col_spacing) * dimensions[1], np.array(row_spacing) * dimensions[0]].T
        self._ENDEL = records.ENDEL()

    @property
    def ref_name(self):
        return self._SNAME.name

    @ref_name.setter
    def ref_name(self, ref_name: str):
        self._SNAME.name = ref_name

    @property
    def coordinates(self):
        return self._XY.x.copy(), self._XY.y.copy()

    @coordinates.setter
    def coordinates(self, xy: np.ndarray[int]):
        if xy.shape[0] != 3 or xy.shape[1] != 2: RuntimeError()
        self._XY.x = xy[:, 0].copy()
        self._XY.y = xy[:, 1].copy()

    @property
    def dimensions(self):
        return self._COLROW.n_rows, self._COLROW.n_cols

    @dimensions.setter
    def dimensions(self, value: typing.Tuple[int, int]):
        rows, cols = value
        self._COLROW.n_rows = rows
        self._COLROW.n_cols = cols

    @classmethod
    def read(cls, reader: Reader) -> ArrayReferenceElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._AREF = records.AREF.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._SNAME = records.SNAME.read(record)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.STRANS:
            self._TRANSFORMATION = StructureTransformationElement.read(reader)

        self._COLROW = records.COLROW.read(reader.current)
        self._XY = records.XY.read(reader.read_next())
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._AREF.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._SNAME.write(stream)
        self._TRANSFORMATION.write(stream) if self._TRANSFORMATION is not None else None
        self._COLROW.write(stream)
        self._XY.write(stream)
        super().write(stream)

    def _draw(self, lib, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        scale = options["scale"]
        x, y = self.coordinates
        x = x * lib.logical_unit * scale
        y = y * lib.logical_unit * scale

        x += shift[0]
        y += shift[1]
        n_rows, n_cols = self.dimensions
        structure = lib[self.ref_name]

        ref = np.array([x[0], y[0]])
        row_spacing = np.array([x[2] - x[0], y[2] - y[0]]) // n_rows
        col_spacing = np.array([x[1] - x[0], y[1] - y[0]]) // n_cols

        for i in range(n_rows):
            for j in range(n_cols):
                for element in structure:
                    shift = ref + i * row_spacing + j * col_spacing
                    layers = element._draw(lib, layers, options, (shift[0], shift[1]))

        return layers


class TextElement(Element):
    """
    TEXT [ELFLAGS] [PLEX] LAYER <textbody> ENDEL
    """

    _TEXT: records.TEXT
    _LAYER: records.LAYER
    _TEXTBODY: TextElement.TextBody

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None

    def __init__(self,
                 text: str,
                 layer: int,
                 xy: typing.Tuple[int, int]
                 ):
        super().__init__()
        self._TEXT = records.TEXT()
        self._LAYER = records.LAYER(layer)
        self._TEXTBODY = TextElement.TextBody(text, xy)
        self._ENDEL = records.ENDEL()

    @property
    def layer(self):
        return self._LAYER.layer

    @layer.setter
    def layer(self, layer: int):
        self._LAYER.layer = layer

    @property
    def text(self):
        return self._TEXTBODY.text

    @text.setter
    def text(self, text: str):
        self._TEXTBODY.text = text

    @property
    def coordinates(self):
        return self._TEXTBODY.coordinates

    @coordinates.setter
    def coordinates(self, xy: typing.Tuple[int, int]):
        self._TEXTBODY.coordinates = xy

    @property
    def pathtype(self):
        return self._TEXTBODY.pathtype

    @pathtype.setter
    def pathtype(self, path_type: gdstypes.PathType):
        self._TEXTBODY.pathtype = path_type

    @property
    def width(self):
        return self._TEXTBODY.width

    @width.setter
    def width(self, width: int):
        self._TEXTBODY.width = width

    @property
    def vertical_alignment(self):
        return self._TEXTBODY.vertical_alignment

    @property
    def horizontal_alignment(self):
        return self._TEXTBODY.horizontal_alignment

    class TextBody(list):
        """
        TEXTTYPE [PRESENTATION] [PATHTYPE] [WIDTH] [<strans>] XY STRING {<property>}*
        """

        _TEXTTYPE: records.TEXTTYPE
        _XY: records.XY
        _STRING: records.STRING

        _DATATYPE: records.DATATYPE = None
        _PRESENTATION: records.PRESENTATION = None
        _PATHTYPE: records.PATHTYPE = None
        _WIDTH: records.WIDTH = None
        _TRANSFORMATION: StructureTransformationElement = None

        def __init__(self,
                     text: str,
                     xy: typing.Tuple[int, int],
                     width: int = 0,
                     pathtype: gdstypes.PathType = gdstypes.PathType.BUTT,
                     datatype: gdstypes.DataType = gdstypes.DataType.NO_DATA_PRESENT):
            super().__init__()
            self._TEXTTYPE = records.TEXTTYPE()
            self._XY = records.XY()
            self.coordinates = xy
            self._STRING = records.STRING(text)
            if width != 0: self._WIDTH = records.WIDTH(width)
            if pathtype != gdstypes.PathType.BUTT: self._PATHTYPE = records.PATHTYPE(pathtype)
            if datatype != gdstypes.DataType.NO_DATA_PRESENT: self._DATATYPE = records.DATATYPE(datatype)

        @property
        def text(self):
            return self._STRING.text

        @text.setter
        def text(self, text: str):
            self._STRING.text = text

        @property
        def coordinates(self):
            return self._XY.x[0], self._XY.y[0]

        @coordinates.setter
        def coordinates(self, value: typing.Tuple[int, int]):
            x, y = value
            self._XY.x = np.array([x])
            self._XY.y = np.array([y])

        @property
        def pathtype(self):
            try:
                return self._PATHTYPE.type
            except AttributeError:
                return gdstypes.PathType.BUTT

        @pathtype.setter
        def pathtype(self, path_type: gdstypes.PathType):
            try:
                self._PATHTYPE.type = path_type
            except AttributeError:
                self._PATHTYPE = records.PATHTYPE(path_type)

        @property
        def width(self):
            try:
                return self._WIDTH.width
            except AttributeError:
                return 0

        @width.setter
        def width(self, width: int):
            try:
                self._WIDTH.width = width
            except AttributeError:
                self._WIDTH = records.WIDTH(width)

        @property
        def vertical_alignment(self):
            return self._PRESENTATION.vertical_alignment

        @property
        def horizontal_alignment(self):
            return self._PRESENTATION.horizontal_alignment

        @classmethod
        def read(cls, reader: Reader) -> TextElement.TextBody:
            self = cls.__new__(cls)
            list.__init__(self)

            self._TEXTTYPE = records.TEXTTYPE.read(reader.read_next())

            record = reader.read_next()
            if record.record_type is gdstypes.RecordType.DATATYPE:
                self._DATATYPE = records.DATATYPE.read(record)
                record = reader.read_next()

            if record.record_type is gdstypes.RecordType.PRESENTATION:
                self._PRESENTATION = records.PRESENTATION.read(record)
                record = reader.read_next()

            if record.record_type is gdstypes.RecordType.PATHTYPE:
                self._PATHTYPE = records.PATHTYPE.read(record)
                record = reader.read_next()

            if record.record_type is gdstypes.RecordType.WIDTH:
                self._WIDTH = records.WIDTH.read(record)
                record = reader.read_next()

            if record.record_type is gdstypes.RecordType.STRANS:
                self._TRANSFORMATION = StructureTransformationElement.read(reader)

            self._XY = records.XY.read(reader.current)
            self._STRING = records.STRING.read(reader.read_next())

            return self

        def write(self, stream: typing.BinaryIO):
            self._TEXTTYPE.write(stream)
            self._PRESENTATION.write(stream) if self._PRESENTATION is not None else None
            self._PATHTYPE.write(stream) if self._PATHTYPE is not None else None
            self._WIDTH.write(stream) if self._WIDTH is not None else None
            self._TRANSFORMATION.write(stream) if self._TRANSFORMATION is not None else None
            self._XY.write(stream)
            self._STRING.write(stream)

    @classmethod
    def read(cls, reader: Reader) -> TextElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._TEXT = records.TEXT.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._LAYER = records.LAYER.read(record)
        self._TEXTBODY = TextElement.TextBody.read(reader)
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._TEXT.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._LAYER.write(stream)
        self._TEXTBODY.write(stream)
        super().write(stream)

    def _draw(self, lib, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        import cairo
        scale = options["scale"]

        x, y = self.coordinates
        x = x * lib.logical_unit * scale
        y = y * lib.logical_unit * scale

        surf = layers[self.layer]
        ctx = cairo.Context(surf)
        ctx.save()
        utils._parse_font_size(options, ctx, self.layer)

        ctx.scale(1, -1)
        ctx.translate(*shift)
        ctx.move_to(x, -y)

        _, _, w, h, _, _ = ctx.text_extents(self.text)
        ctx.rel_move_to(-w / 2, -h / 2)

        if self.vertical_alignment == gdstypes.VerticalAlignment.TOP:
            ctx.rel_move_to(0, h / 2)
        elif self.vertical_alignment == gdstypes.VerticalAlignment.BOTTOM:
            ctx.rel_move_to(0, -h / 2)

        if self.horizontal_alignment == gdstypes.HorizontalAlignment.LEFT:
            ctx.rel_move_to(w / 2, 0)
        elif self.horizontal_alignment == gdstypes.HorizontalAlignment.RIGHT:
            ctx.rel_move_to(-w / 2, 0)

        ctx.show_text(self.text)

        ctx.restore()
        return layers


class NodeElement(Element):
    """
    NODE [ELFLAGS] [PLEX] LAYER NODETYPE XY {<property>}* ENDEL
    """

    _NODE: records.NODE
    _LAYER: records.LAYER
    _NODETYPE: records.NODETYPE
    _XY: records.XY

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None

    def __init__(self,
                 layer: int,
                 xy: typing.Tuple[int, int],
                 nodetype: int = 0):
        super().__init__()
        self._NODE = records.NODE()
        self._LAYER = records.LAYER(layer)
        self._XY = records.XY()
        self.coordinates = xy
        if nodetype != 0: self._NODETYPE = records.NODETYPE(nodetype)
        self._ENDEL = records.ENDEL()

    @property
    def layer(self):
        return self._LAYER.layer

    @layer.setter
    def layer(self, layer: int):
        self._LAYER.layer = layer

    @property
    def nodetype(self):
        return self._NODETYPE.type

    @nodetype.setter
    def nodetype(self, nodetype: int):
        self._NODETYPE.type = nodetype

    @property
    def coordinates(self):
        return self._XY.x, self._XY.y

    @coordinates.setter
    def coordinates(self, xy: np.ndarray):
        if xy.shape[1] != 2: RuntimeError()
        self._XY.x = xy[:, 0]
        self._XY.y = xy[:, 1]

    @classmethod
    def read(cls, reader: Reader) -> NodeElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._NODE = records.NODE.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._LAYER = records.LAYER.read(record)
        self._NODETYPE = records.NODETYPE.read(reader.read_next())
        self._XY = records.XY.read(reader.read_next())
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._NODE.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._LAYER.write(stream)
        self._NODETYPE.write(stream)
        self._XY.write(stream)
        super().write(stream)


class BoxElement(Element):
    """
    BOX [ELFLAGS] [PLEX] LAYER BOXTYPE XY {<property>}* ENDEL
    """

    _BOX: records.BOX
    _LAYER: records.LAYER
    _BOXTYPE: records.BOXTYPE
    _XY: records.XY

    _ELFLAGS: records.ELFLAGS = None
    _PLEX: records.PLEX = None

    def __init__(self,
                 layer: int,
                 xy: typing.Tuple[int, int],
                 boxtype: int = 0):
        super().__init__()
        self._BOX = records.BOX()
        self._LAYER = records.LAYER(layer)
        self._XY = records.XY()
        self.coordinates = xy
        if boxtype != 0: self._BOXTYPE = records.BOXTYPE(boxtype)
        self._ENDEL = records.ENDEL()

    @property
    def layer(self):
        return self._LAYER.layer

    @layer.setter
    def layer(self, layer: int):
        self._LAYER.layer = layer

    @property
    def boxtype(self):
        return self._BOXTYPE.type

    @boxtype.setter
    def boxtype(self, boxtype: int):
        self._BOXTYPE.type = boxtype

    @property
    def coordinates(self):
        return self._XY.x.copy(), self._XY.y.copy()

    @coordinates.setter
    def coordinates(self, xy: np.ndarray[int]):
        if xy.shape[1] != 2 or xy.shape[0] != 5 or xy[0, :] != xy[-1, :]: RuntimeError()
        self._XY.x = xy[:, 0]
        self._XY.y = xy[:, 1]

    @classmethod
    def read(cls, reader: Reader) -> BoxElement:
        self = cls.__new__(cls)
        list.__init__(self)

        self._BOX = records.BOX.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.ELFLAGS:
            self._ELFLAGS = records.ELFLAGS.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.PLEX:
            self._PLEX = records.PLEX.read(record)
            record = reader.read_next()

        self._LAYER = records.LAYER.read(record)
        self._BOXTYPE = records.BOXTYPE.read(reader.read_next())
        self._XY = records.XY.read(reader.read_next())
        self._read_properties(reader)

        return self

    def write(self, stream):
        self._BOX.write(stream)
        self._ELFLAGS.write(stream) if self._ELFLAGS is not None else None
        self._PLEX.write(stream) if self._PLEX is not None else None
        self._LAYER.write(stream)
        self._BOXTYPE.write(stream)
        self._XY.write(stream)
        super().write(stream)

    def _draw(self, lib, layers, options, shift: typing.Tuple[int, int] = (0, 0)):
        import cairo
        scale = options["scale"]

        X, Y = self.coordinates
        X = X * lib.logical_unit * scale
        Y = Y * lib.logical_unit * scale

        surf = layers[self.layer]
        ctx = cairo.Context(surf)
        ctx.save()
        utils._parse_line_width(options, ctx, self.layer)

        ctx.translate(*shift)
        ctx.move_to(X[0], Y[0])
        for x, y in zip(X[1:], Y[1:]):
            ctx.line_to(x, y)

        ctx.close_path()
        ctx = utils._parse_fill_color(options, ctx, self.layer)
        ctx = utils._parse_pattern(options, ctx, self.layer)
        ctx.fill_preserve()

        ctx = utils._parse_stroke_color(options, ctx, self.layer)
        ctx.stroke()

        ctx.restore()
        return layers


class StructureTransformationElement:
    """
    STRANS [MAG] [ANGLE]
    """

    _STRANS: records.STRANS

    _MAG: records.MAG = None
    _ANGLE: records.ANGLE = None

    @property
    def reflect_about_x(self):
        return self._STRANS.reflect_about_x

    @reflect_about_x.setter
    def reflect_about_x(self, value: bool):
        self._STRANS.reflect_about_x = value

    @property
    def absolute_magnification(self):
        return self._STRANS.absolute_magnification

    @absolute_magnification.setter
    def absolute_magnification(self, value: bool):
        self._STRANS.absolute_magnification = value

    @property
    def absolute_angle(self):
        return self._STRANS.absolute_angle

    @absolute_angle.setter
    def absolute_angle(self, value: bool):
        self._STRANS.absolute_angle = value

    @property
    def magnification_factor(self):
        try:
            return self._MAG.magnification_factor
        except AttributeError:
            return 1

    @magnification_factor.setter
    def magnification_factor(self, factor: float):
        try:
            self._MAG.magnification_factor = factor
        except AttributeError:
            self._MAG = records.MAG(factor)

    @property
    def angular_rotation_factor(self):
        try:
            return self._ANGLE.angular_rotation_factor
        except AttributeError:
            return 0

    @angular_rotation_factor.setter
    def angular_rotation_factor(self, factor: float):
        try:
            self._ANGLE.angular_rotation_factor = factor
        except AttributeError:
            self._ANGLE = records.ANGLE(factor)

    @classmethod
    def read(cls, reader: Reader) -> StructureTransformationElement:
        self = cls.__new__(cls)

        self._STRANS = records.STRANS.read(reader.current)

        record = reader.read_next()
        if record.record_type is gdstypes.RecordType.MAG:
            self._MAG = records.MAG.read(record)
            record = reader.read_next()

        if record.record_type is gdstypes.RecordType.ANGLE:
            self._ANGLE = records.ANGLE.read(record)
            reader.read_next()

        return self

    def write(self, stream: typing.BinaryIO):
        self._STRANS.write(stream)
        self._MAG.write(stream) if self._MAG is not None else None
        self._ANGLE.write(stream) if self._ANGLE is not None else None


class RawRecord:
    def __init__(self, record_type, data_type, data):
        self.record_type = record_type
        self.data_type = data_type
        self.data = data


class Reader:
    def __init__(self, stream: typing.BinaryIO):
        self.stream = stream
        self.current = None

    def __iter__(self):
        return self

    def __next__(self):
        if header := self.stream.read(4):
            # extract count, record type and data type
            # first two bytes: total record length
            # third byte: record type
            # fourth byte: type of data contained within the record.
            record_size, record_type, data_type = struct.unpack(">HBB", header)
            data_size = record_size - 4  # calculate data size by subtracting header size from total record size
            record_type = gdstypes.RecordType(record_type)
            data_type = gdstypes.DataType(data_type)
            data = self.stream.read(data_size)
            self.current = RawRecord(record_type, data_type, data)
            return self.current
        else:
            raise StopIteration()

    def revert(self):
        """
        reverts the last read
        """
        self.stream.seek(-len(self.current.data) - 4, io.SEEK_CUR)
        self.current = None

    def read_next(self) -> RawRecord:
        return next(self)
