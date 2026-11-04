"""What the guided setup offers for this driver, and the keys its entry takes.

Building an entry checks its keys against :data:`KNIFE` first: an unknown key, or a
value of another type than the key's default, fails the build with the key named,
and the builder gets the entry's options with every default filled in. Imports
nothing but the setup records.
"""

from fibsem.drivers.setup import SetupDevice, SetupKey

KNIFE = SetupDevice(
    type="knife",
    label="KnifeCo knife",
    summary="A knife on its own controller.",
    name="knife",
    keys=(
        SetupKey("address", "127.0.0.1", "Address", "Where the knife's controller is."),
        SetupKey("speed", 1e-4, "Speed", "The cutting speed it starts at, in m/s."),
    ),
    role=None,  # it fills no role on a beam (the scanner fills one)
)
