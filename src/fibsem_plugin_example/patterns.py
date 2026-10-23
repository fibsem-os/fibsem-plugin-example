"""An example milling pattern.

Draws a crosshair: two crossed bars centred on the pattern's point. Useful as a
registration marker, and small enough to read in one sitting.

Registered as a `fibsem.milling.patterns` entry point in pyproject.toml. Once installed
it appears in the pattern dropdown of the milling widget alongside the built-in
patterns, and can be used from a protocol yaml by name.
"""

from dataclasses import dataclass
from typing import ClassVar

from fibsem.milling.patterning.base import BasePattern
from fibsem.structures import FibsemRectangleSettings, distance_param, param


@dataclass
class ExamplePluginPattern(BasePattern[FibsemRectangleSettings]):
    """A crosshair marker: one horizontal bar, one vertical bar."""

    # `name` is what the user sees in the pattern dropdown, and what a protocol
    # yaml refers to. It must be unique across all patterns -- if it collides
    # with a built-in, the built-in wins and yours is silently shadowed.
    name: ClassVar[str] = "Example Plugin"

    # Every field is rendered as a form control in the milling widget, and the
    # field's Parameter is what drives that: its SI unit, its limits in SI, a
    # doc for the tooltip, and a `Display` saying how the form shows it (label,
    # scale, step, decimals). `param(default, ...)` from fibsem.structures
    # declares the field with those as keyword arguments, so a misspelled key
    # is a TypeError when your plugin is imported rather than a form that
    # renders without its label. The value stays a plain float; the form reads
    # `ExamplePluginPattern.params.length`.
    #
    # Any field that holds a distance takes `distance_param(label, doc)`,
    # as the built-in patterns do. Values are stored in **metres**, but nobody
    # wants to type 0.00002, so it shows them in microns (scale 1e6, "µm") and
    # carries sensible limits, step and decimals with it.
    #
    # Leaving it out is the single easiest way to ship a broken-looking plugin:
    # with no scale the form shows the value as it is, and a perfectly correct
    # 20 um default renders as "0.000 m". The value is right; it just looks
    # empty. test_distance_fields_declare_a_scale guards this.
    length: float = param(
        20.0e-6, distance_param("Length", "Length of each bar of the crosshair.")
    )
    thickness: float = param(
        2.0e-6, distance_param("Thickness", "Width of each bar of the crosshair.")
    )
    depth: float = param(1.0e-6, distance_param("Depth", "Milling depth."))

    def define(self) -> list[FibsemRectangleSettings]:
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
