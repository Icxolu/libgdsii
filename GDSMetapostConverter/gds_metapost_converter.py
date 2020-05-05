import typing
import libgdsii
import numpy as np


class GDSMetapostConverter:
    _layers: typing.Dict[int, str] = { }
    _layer_drawcolor: typing.Dict[int, str] = { }
    _layer_fillcolor: typing.Dict[int, str] = { }
    _layer_filltransparency: typing.Dict[int, float] = { }

    @property
    def all_layers(self):
        return self._all_layers

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self._scale = scale

    @property
    def layer_order(self):
        return self._layer_order

    @layer_order.setter
    def layer_order(self, value):
        self._layer_order = value

    def __init__(self, lib: libgdsii.Library, scale: float = 1, layer_order: typing.List[int] = None,
                 layer_drawcolor: typing.Dict[int, str] = { }, layer_fillcolor: typing.Dict[int, str] = { },
                 layer_filltransparency: typing.Dict[int, float] = { }):
        self._lib = lib
        self._layer_drawcolor = layer_drawcolor
        self._layer_fillcolor = layer_fillcolor
        self._layer_filltransparency = layer_filltransparency
        self.scale = scale
        self.tmp = 10000

        self._all_layers = sorted(set(
                [element.layer for structure in lib.values() for element in structure if hasattr(element, "layer")]
        ))
        self._layer_order = layer_order if layer_order is not None else self._all_layers

    def parse(self):
        structure: libgdsii.Structure
        element: libgdsii.Element
        for structure in self._lib.values():
            for element in structure:
                self._parse_element(element)

    def _parse_element(self, element: libgdsii.Element, shift: typing.Tuple[int, int] = (0, 0)):
        if type(element) is libgdsii.Boundary:
            self._draw_boundary(element, shift)
        elif type(element) is libgdsii.Path:
            self._draw_path(element, shift)
        elif type(element) is libgdsii.RaithCircle:
            self._draw_raith_circle(element, shift)
        elif type(element) is libgdsii.Text:
            self._draw_text(element, shift)
        elif type(element) is libgdsii.StructureReference:
            self._draw_reference_structure(element, shift)
        elif type(element) is libgdsii.ArrayReference:
            self._draw_array_reference(element, shift)
        else:
            print(type(element))

    def _draw_boundary(self, element: libgdsii.Boundary, shift: typing.Tuple[int, int]):
        X, Y = element.coordinates
        X += shift[0]
        Y += shift[1]
        txt = " -- ".join([f"({x / self.tmp}u, {y / self.tmp}u)" for x, y in zip(X, Y)])
        draw = f"draw {txt} -- cycle withcolor {self._layer_drawcolor.get(element.layer, 'black')};\n"
        fill = f"fill {txt} -- cycle withcolor {self._layer_fillcolor.get(element.layer, 'white')} withtransparency (\"normal\", {self._layer_filltransparency.get(element.layer, .5)});\n"
        try:
            self._layers[element.layer] += fill + draw
        except KeyError:
            self._layers[element.layer] = fill + draw

    def _draw_box(self, element: libgdsii.Box, shift: typing.Tuple[int, int]):
        X, Y = element.coordinates
        X += shift[0]
        Y += shift[1]
        txt = " -- ".join([f"({x / self.tmp}u, {y / self.tmp}u)" for x, y in zip(X, Y)])
        txt = "draw " + txt + " -- cycle;"

    def _draw_path(self, element: libgdsii.Path, shift: typing.Tuple[int, int]):
        X, Y = element.coordinates
        X += shift[0]
        Y += shift[1]
        txt = " -- ".join([f"({x / self.tmp}u, {y / self.tmp}u)" for x, y in zip(X, Y)])
        txt = f"draw {txt} withpen pencircle scaled {element.width / self.tmp}u;\n"
        try:
            self._layers[element.layer] += txt
        except KeyError:
            self._layers[element.layer] = txt

    def _draw_text(self, element: libgdsii.Text, shift: typing.Tuple[int, int]):
        x, y = element.coordinates
        x += shift[0]
        y += shift[1]
        if (element.vertical_alignment == libgdsii.VerticalAlignment.TOP) and (
                element.horizontal_alignment == libgdsii.HorizontalAlignment.CENTER):
            txt = "label.bot"
        if (element.vertical_alignment == libgdsii.VerticalAlignment.BOTTOM) and (
                element.horizontal_alignment == libgdsii.HorizontalAlignment.CENTER):
            txt = "label.top"
        elif (element.vertical_alignment == libgdsii.VerticalAlignment.TOP) and (
                element.horizontal_alignment == libgdsii.HorizontalAlignment.LEFT):
            txt = "label.lrt"
        elif (element.vertical_alignment == libgdsii.VerticalAlignment.TOP) and (
                element.horizontal_alignment == libgdsii.HorizontalAlignment.RIGHT):
            txt = "label.llft"
        elif (element.vertical_alignment == libgdsii.VerticalAlignment.BOTTOM) and (
                element.horizontal_alignment == libgdsii.HorizontalAlignment.LEFT):
            txt = "label.urt"
        elif (element.vertical_alignment == libgdsii.VerticalAlignment.BOTTOM) and (
                element.horizontal_alignment == libgdsii.HorizontalAlignment.RIGHT):
            txt = "label.ulft"
        else:
            txt = "label"
        txt += f"(\"{element.text}\", ({x / self.tmp}u, {y / self.tmp}u));\n"
        try:
            self._layers[element.layer] += txt
        except KeyError:
            self._layers[element.layer] = txt

    def _draw_raith_circle(self, element: libgdsii.RaithCircle, shift: typing.Tuple[int, int]):
        x, y = element.center
        x += shift[0]
        y += shift[1]
        txt = f"fullcircle "
        if element.is_ellipse:
            txt += f"xscaled {2 * element.radii[0] / self.tmp}u yscaled {2 * element.radii[1] / self.tmp}u "
        else:
            txt += f"scaled {2 * element.radii[0] / self.tmp}u "
        txt += f"shifted ({x / self.tmp}u, {y / self.tmp}u)"

        draw = f"draw {txt} withcolor {self._layer_drawcolor.get(element.layer, 'black')};\n"
        if element.is_filled:
            fill = f"fill {txt} withcolor {self._layer_fillcolor.get(element.layer, 'white')} withtransparency (\"normal\", {self._layer_filltransparency.get(element.layer, .5)});\n"
        else:
            fill = ""

        try:
            self._layers[element.layer] += fill + draw
        except KeyError:
            self._layers[element.layer] = fill + draw

    def _draw_reference_structure(self, element: libgdsii.StructureReference, shift: typing.Tuple[int, int]):
        x, y = element.coordinates
        x += shift[0]
        y += shift[1]
        structure = self._lib[element.ref_name]

        for element in structure:
            self._parse_element(element, (x, y))

    def _draw_array_reference(self, element: libgdsii.ArrayReference, shift: typing.Tuple[int, int]):
        x, y = element.coordinates
        x += shift[0]
        y += shift[1]
        n_rows, n_cols = element.dimensions
        structure = self._lib[element.ref_name]

        ref = np.array([x[0], y[0]])
        row_spacing = np.array([x[2] - x[0], y[2] - y[0]]) // n_rows
        col_spacing = np.array([x[1] - x[0], y[1] - y[0]]) // n_cols
        print(n_rows, row_spacing, n_cols, col_spacing)

        for i in range(n_rows):
            for j in range(n_cols):
                for element in structure:
                    shift = ref + i * row_spacing + j * col_spacing
                    self._parse_element(element, (shift[0], shift[1]))

    def save(self, stream: typing.TextIO):
        self.parse()
        stream.write("\\starttext\n\\startMPpage\nnumeric u; u := 1cm;\n")
        for layer in self._layer_order:
            try:
                stream.write(self._layers[layer])
            except KeyError:
                pass
        stream.write("\\stopMPpage\n\\stoptext")
