"""The chamber lamp as a fibsem device, and its builder.

A device class declares its parameters; for each one it defines ``read_<name>``
(the parameter exists), ``write_<name>`` (it can be set; without it, read-only) and
optionally ``metadata_<name>`` (limits the hardware reports at run time). Limits
declared on the parameter are checked before ``write_`` is called: a value outside
them is clipped, with a warning.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict

from fibsem.devices import Device, DeviceParameter, Resources
from fibsem.structures.params import Display, RangeLimit

if TYPE_CHECKING:
    from fibsem.drivers.registry import BuildContext
    from fibsem.structures.system import DeviceEntry


class LampController:
    """A stand-in for the lamp's own controller library. Knows nothing about fibsem."""

    serial = "LC-0001"

    def __init__(self, address: str):
        self.address = address
        self.on = False
        self.level = 0.5
        self._lit_since = 0.0
        self._hours = 120.0

    def switch(self, on: bool) -> None:
        if on and not self.on:
            self._lit_since = time.monotonic()
        if not on and self.on:
            self._hours += (time.monotonic() - self._lit_since) / 3600
        self.on = on

    def hours(self) -> float:
        lit = (time.monotonic() - self._lit_since) / 3600 if self.on else 0.0
        return self._hours + lit


class Lamp(Device):
    """A lamp that lights the chamber for the chamber camera."""

    on = DeviceParameter(bool, doc="Whether the lamp is lit.")
    brightness = DeviceParameter(
        float,
        limits=RangeLimit(0.0, 1.0),
        doc="How bright the lamp is, as a fraction of full.",
        display=Display("Brightness", scale=100, unit="%", step=5, decimals=0),
    )
    hours = DeviceParameter(
        float, unit="h", doc="How long the lamp has been lit in all, in hours."
    )

    def __init__(self, name: str, controller: LampController, parent: Any = None, **kw):
        super().__init__(name, parent, **kw)
        self._controller = controller

    def facts(self) -> Dict[str, Any]:
        return {"serial": self._controller.serial, "address": self._controller.address}

    def read_on(self) -> bool:
        return self._controller.on

    def write_on(self, value: bool) -> None:
        self._controller.switch(value)

    def read_brightness(self) -> float:
        return self._controller.level

    def write_brightness(self, value: float) -> None:
        self._controller.level = value

    # no write_hours: the lamp counts them, so the parameter is read-only
    def read_hours(self) -> float:
        return self._controller.hours()


def build_lamp(entry: "DeviceEntry", context: "BuildContext") -> Lamp:
    """The lamp a ``type: lamp, driver: LampCo`` entry names. Its own resources:
    changing it doesn't wait for the microscope's locks."""
    controller = LampController(str(entry.options.get("address", "127.0.0.1")))
    return Lamp(
        entry.name, controller, parent=context.microscope, resources=Resources()
    ).connect()
