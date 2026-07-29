"""An example milling pattern.

Draws a crosshair: two crossed bars centred on the pattern's point. Useful as a
registration marker, and small enough to read in one sitting.

Registered as a `fibsem.patterns` entry point in pyproject.toml. Once installed
it appears in the pattern dropdown of the milling widget alongside the built-in
patterns, and can be used from a protocol yaml by name.
"""

from dataclasses import dataclass, field
from typing import ClassVar, List

# These two imports, and nothing else from fibsem. That constraint is real and
# it is the reason this plugin is three modules rather than one.
#
# `fibsem/milling/base.py` imports `fibsem.milling.patterning`, whose __init__
# ends with a module-level `MILLING_PATTERNS = get_patterns()`. So your pattern
# plugin is imported *while `fibsem.milling.base` is only partially
# initialised*. Two things follow:
#
#   1. Do not import from the `fibsem.milling.patterning` package. Names
#      defined below that snapshot -- MILLING_PATTERNS, MILLING_PATTERN_NAMES,
#      PROTOCOL_MILL_MAP -- do not exist yet. Use `patterns2`, which is fully
#      imported by then.
#
#   2. Do not import anything that reaches back into `fibsem.milling.base` --
#      that includes `fibsem.milling.tasks` and everything under
#      `fibsem.applications`. Putting your pattern in the same module as your
#      task is enough to trip this.
#
# Either one raises ImportError, the plugin loader catches it, and your pattern
# simply never appears. There is no error in the app: the only trace is an
# ERROR line in the log file.
#
# Strategies and tasks have no such restriction -- their registries are built
# later, once fibsem is fully imported.
from fibsem.milling.patterning.patterns2 import BasePattern
from fibsem.milling.properties import DEFAULT_DISTANCE_METADATA
from fibsem.structures import FibsemRectangleSettings


@dataclass
class ExamplePluginPattern(BasePattern[FibsemRectangleSettings]):
    """A crosshair marker: one horizontal bar, one vertical bar."""

    # `name` is what the user sees in the pattern dropdown, and what a protocol
    # yaml refers to. It must be unique across all patterns -- if it collides
    # with a built-in, the built-in wins and yours is silently shadowed.
    name: ClassVar[str] = "Example Plugin"

    # Every field is rendered as a form control in the milling widget, and the
    # field metadata is what drives that.
    #
    # Spread DEFAULT_DISTANCE_METADATA into any field that holds a distance.
    # Values are stored in **metres**, but nobody wants to type 0.00002, so the
    # widget scales for display -- `scale: 1e6` turns metres into microns and
    # the suffix into "um", and it carries sensible `minimum`, `maximum`,
    # `step` and `decimals` with it.
    #
    # Leaving it out is the single easiest way to ship a broken-looking plugin:
    # `scale` defaults to None, the widget falls back to a scale of 1, and a
    # perfectly correct 20 um default renders as "0.000 m". The value is right;
    # it just looks empty. test_distance_fields_declare_a_scale guards this.
    length: float = field(
        default=20.0e-6,
        metadata={
            **DEFAULT_DISTANCE_METADATA,
            "label": "Length",
            "tooltip": "Length of each bar of the crosshair.",
        },
    )
    thickness: float = field(
        default=2.0e-6,
        metadata={
            **DEFAULT_DISTANCE_METADATA,
            "label": "Thickness",
            "tooltip": "Width of each bar of the crosshair.",
        },
    )
    depth: float = field(
        default=1.0e-6,
        metadata={
            **DEFAULT_DISTANCE_METADATA,
            "label": "Depth",
            "tooltip": "Milling depth.",
        },
    )

    def define(self) -> List[FibsemRectangleSettings]:
        """Return the shapes to mill, in microscope coordinates (metres).

        This is the only method you have to implement. It is called every time
        the pattern is drawn or re-drawn, so it must be cheap and must not
        touch the microscope.

        `self.point` is where the user placed the pattern; offset everything
        from it rather than assuming the origin.
        """
        horizontal = FibsemRectangleSettings(
            width=self.length,
            height=self.thickness,
            depth=self.depth,
            centre_x=self.point.x,
            centre_y=self.point.y,
        )
        vertical = FibsemRectangleSettings(
            width=self.thickness,
            height=self.length,
            depth=self.depth,
            centre_x=self.point.x,
            centre_y=self.point.y,
        )

        # Assigning to self.shapes is the convention the base class expects;
        # returning the list is what the caller uses.
        self.shapes = [horizontal, vertical]
        return self.shapes
