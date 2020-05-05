# libgdsii

libgdsii is a python library to load a gds(ii) layout file into a python object tree. This object tree can be modified or even created from scratch. The final tree can be saved as a gds(ii) file again.

The parser is implemented to follow the gds(ii) spec (eg. [pdf](http://bitsavers.informatik.uni-stuttgart.de/pdf/calma/GDS_II_Stream_Format_Manual_6.0_Feb87.pdf)). If it encounters non spec behavior it gives a warning, but continues reading. Also the non spec record ``RaithCircle``, which is used by RAITH machines, is implemented. Parsing info was taken from [python-gdsii-raith](https://github.com/cdoolin/python-gdsii-raith).

The library also has the possibility to create an image of the layout using the python bindings ``pycairo`` of the well known ``cairo`` library, see the [examples](./examples) for more info.

For reading an writing gds(ii) files only the ``numpy`` library is necessary, but for the drawing capabilities ``pycairo`` need to be installed.

## Installation
To install ``libgdsii`` use the following command.

```
pip install git+https://github.com/Icxolu/libgdsii
````

The drawing feature needs ``pycairo``, windows user might want to use a prebuilt binary from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pycairo) using
```
pip install <pycairo filename>.whl
```

Linux user may take a look [here](https://pycairo.readthedocs.io/en/latest/getting_started.html).

## Usage
Please take a look at the [examples](./examples).
