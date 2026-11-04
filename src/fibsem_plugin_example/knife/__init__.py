"""A knife on its own controller: a new device type with commands, a guided setup,
a fault when its controller is offline, and steps of its own in the hardware check.

The same shape as a real driver: ``sdk.py`` stands in for the vendor's library,
``devices.py`` is the fibsem device over it, ``setup.py`` is what the guided setup
offers, and this module holds only the record. Name it on a ``hardware.devices``
entry::

    hardware:
      devices:
        - name: knife
          type: knife
          driver: KnifeCo
          address: 127.0.0.1
"""

from fibsem.drivers.registry import DeviceBuilder, DriverEntry

MANUFACTURER = "KnifeCo"


def driver() -> DriverEntry:
    """The ``fibsem.drivers`` entry point: this driver's record."""
    return DriverEntry(
        manufacturer=MANUFACTURER,
        devices={
            "knife": DeviceBuilder("fibsem_plugin_example.knife.devices:build_knife")
        },
        # offered in the guided setup; its keys are the entry's schema
        setup="fibsem_plugin_example.knife.setup:KNIFE",
    )
