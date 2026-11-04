"""A chamber lamp: the smallest device driver, a new device type with settings only.

Two files: this one holds only the driver's record, so listing the drivers imports
nothing else, and ``devices.py`` holds the device and its builder. No guided setup
(see ``knife/`` for one), so an entry's keys are not checked. Name it on a
``hardware.devices`` entry::

    hardware:
      devices:
        - name: lamp
          type: lamp
          driver: LampCo
          address: 127.0.0.1
"""

from fibsem.drivers.registry import DeviceBuilder, DriverEntry

MANUFACTURER = "LampCo"


def driver() -> DriverEntry:
    """The ``fibsem.drivers`` entry point: this driver's record."""
    return DriverEntry(
        manufacturer=MANUFACTURER,
        devices={
            "lamp": DeviceBuilder("fibsem_plugin_example.lamp.devices:build_lamp")
        },
    )
