"""The knife as a fibsem device, and its builder.

Beyond the lamp, this shows: limits the hardware reports (``metadata_angle``),
commands (``cut``), the vendor's error turned into a ``DeviceFault``, a hardware
check step, and a device that owns its controller connection and closes it on
disconnect.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from fibsem.devices import (
    Device,
    DeviceFault,
    DeviceParameter,
    ParameterMetadata,
    Resources,
    command,
)
from fibsem.structures.params import Display, RangeLimit

from fibsem_plugin_example.knife.sdk import ControllerError, KnifeController

if TYPE_CHECKING:
    from fibsem.drivers.registry import BuildContext
    from fibsem.structures.system import DeviceEntry

DEGREES = 180 / 3.141592653589793


class Knife(Device):
    """A knife that cuts the block face."""

    angle = DeviceParameter(
        float,
        unit="rad",
        doc="The knife's angle to the block face.",
        display=Display("Angle", scale=DEGREES, unit="°", step=0.5, decimals=1),
    )
    speed = DeviceParameter(
        float,
        unit="m/s",
        limits=RangeLimit(1e-6, 1e-3),
        doc="How fast the knife moves through a cut.",
        display=Display("Speed", scale=1e6, step=10, decimals=0),
    )
    cuts = DeviceParameter(int, doc="How many cuts this knife has made.")

    def __init__(
        self, name: str, controller: KnifeController, parent: Any = None, **kw
    ):
        super().__init__(name, parent, **kw)
        self._controller = controller

    def facts(self) -> Dict[str, Any]:
        c = self._controller
        return {"serial": c.serial, "firmware": c.firmware, "address": c.address}

    @command
    def cut(self) -> int:
        """Make one cut, and return how many the knife has made."""
        try:
            return self._controller.cut()
        except ControllerError as e:
            # the controller refused: a device fault naming the knife, not the SDK's
            # own error, so the App Server answers 502 and a client can tell it apart
            raise DeviceFault(str(e), device=self.name) from e

    def hardware_check(self, report: Any, level: Any) -> None:
        """The READ step every device has, then at SETTINGS the speed changed, read
        back and put back. No step cuts: a check must not move anything."""
        from fibsem.tools.hardware_check import Level, check_round_trip

        super().hardware_check(report, level)
        if level.includes(Level.SETTINGS):
            speed = self.speed.get_value()
            check_round_trip(self, "speed", 2e-4 if speed != 2e-4 else 1e-4, report)

    def disconnect(self) -> None:
        # this knife owns its connection (the scanner's builder shares one instead)
        self._controller.close()
        super().disconnect()

    # -- parameters

    def read_angle(self) -> float:
        return self._controller.angle

    def write_angle(self, value: float) -> None:
        self._controller.angle = value

    def metadata_angle(self) -> ParameterMetadata:
        # the limit this unit reports, not one fixed in the class
        return ParameterMetadata(limits=RangeLimit(0.0, self._controller.max_angle))

    def read_speed(self) -> float:
        return self._controller.speed

    def write_speed(self, value: float) -> None:
        self._controller.speed = value

    def read_cuts(self) -> int:
        return self._controller.cuts


def build_knife(entry: "DeviceEntry", context: "BuildContext") -> Knife:
    """The knife a ``type: knife, driver: KnifeCo`` entry names, with its keys
    checked against ``setup.KNIFE`` and its defaults filled in."""
    options = entry.options
    try:
        controller = KnifeController(str(options["address"]))
    except ControllerError as e:
        raise DeviceFault(str(e), device=entry.name) from e
    controller.speed = float(options["speed"])
    return Knife(
        entry.name, controller, parent=context.microscope, resources=Resources()
    ).connect()
