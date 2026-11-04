"""A stand-in for a knife vendor's SDK: a controller on its own cable.

Nothing here knows about fibsem. Open a connection by address, set the angle and
speed, make a cut, close it.
"""

from __future__ import annotations


class ControllerError(RuntimeError):
    pass


class KnifeController:
    """One connection to the knife at *address*."""

    serial = "KC-0001"
    firmware = "2.0.1"
    max_angle = 0.5  # rad; what this unit's mount allows

    def __init__(self, address: str):
        if not address:
            raise ControllerError("no address")
        self.address = address
        self.open = True
        self.angle = 0.1
        self.speed = 1e-4
        self.cuts = 0

    def close(self) -> None:
        self.open = False

    def _check(self) -> None:
        if not self.open:
            raise ControllerError(f"controller at {self.address} is offline")

    def cut(self) -> int:
        self._check()
        self.cuts += 1
        return self.cuts
