# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.4.2
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Inverter Example
# Example gds file taken from http://www.yzuda.org/download/_GDSII_examples.html.

# %% [markdown]
# ## Load gds file into python

# %%
from libgdsii import Library

with open("inv.gds2", "rb") as file:
    lib = Library.load_from_file(file)

# %% [markdown]
# The available layer are:

# %%
lib.layers

# %% [markdown]
# The contained structures are:

# %%
lib.keys()

# %% [markdown]
# ## Do a very basic plot of the layout
# (The ``wand`` library is used to display the PDF in the notebook)

# %%
from IPython.display import Image
from io import BytesIO

def plot(pdfio):
    try:
        from wand.image import Image
        img = Image(blob=pdfio.getvalue(), format="pdf", resolution=200)
        img.rotate(90)
        return img
    except Exception as e:
        return e


# %%
pdfio = BytesIO()
lib.draw(pdfio, scale=10)
plot(pdfio)

# %% [markdown]
# The structure in the top left is only a reference structure used in the main structure, therefore it can be removed from the drawing

# %%
options = {
    "structures": ["inv1"]
}
pdfio = BytesIO()
lib.draw(pdfio, scale=10, options=options)
plot(pdfio)

# %% [markdown]
# ## Every picture is better with colors!
#
# Colors and patterns can be controlled using the ``options`` parameter. First the fields in the layer subdict are used, than the toplevel default value and lastly a library default.

# %%
from libgdsii import Color, Pattern

options = {
    "structures": ["inv1"],
    2: {
        "line_width": 2,
        "fill_color": Color(1, 1, 0, .2),
        "stroke_color": Color(1, 1, 0)
    },
    41: {
        "line_width": 1.4,
        "fill_color": Color(0, 1, 0, .2),
        "pattern": Pattern.NORTH_WEST_LINES,
        "stroke_color": Color(0, 1, 0)
    },
    42: {
        "line_width": 1.4,
        "fill_color": Color(1, 0, 0, .2),
        "pattern": Pattern.NORTH_EAST_LINES,
        "stroke_color": Color(1, 0, 0)
    }
}

pdfio = BytesIO()
lib.draw(pdfio, scale=10, options=options)
plot(pdfio)

# %% [markdown]
# ## Layer selection and ordering
# Specific layers, aswell as the layer order can be set using the ``order`` key. If not set, all layer will be rendered in ascending order.

# %%
options = {
    "order": [43, 42, 48],
    "line_width": 2,
    42: {
        "fill_color": Color(1, 1, 0),
        "stroke_color": Color(1, 0, 0)
    },
    43: {
        "fill_color": Color(0, 1, 0),
    }
}

pdfio = BytesIO()
lib.draw(pdfio, scale=10, options=options)
plot(pdfio)

# %% [markdown]
# ## Not so clever layer order (layers 43 and 42 cover layer 48)

# %%
options = {
    "order": [48, 43, 42],
    "line_width": 2,
    42: {
        "fill_color": Color(1, 1, 0),
        "stroke_color": Color(1, 0, 0)
    },
    43: {
        "fill_color": Color(0, 1, 0),
    }
}

pdfio = BytesIO()
lib.draw(pdfio, scale=10, options=options)
plot(pdfio)
