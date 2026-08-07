"""An example milling strategy.

A milling strategy controls *how* a milling stage is executed -- the built-in
Standard strategy sets up the beam once and mills straight through. This one
mills the same patterns in several shorter passes instead, which is a common
way to reduce redeposition and let the sample settle between passes.

Registered as a `fibsem.strategies` entry point in pyproject.toml. Once
installed it appears in the strategy dropdown for every milling stage.
"""

import logging
import threading
from dataclasses import dataclass, field
from typing import Optional

from fibsem.cancellation import raise_if_cancelled
from fibsem.microscope import FibsemMicroscope
from fibsem.milling import setup_milling
from fibsem.milling.base import (
    FibsemMillingStage,
    MillingStrategy,
    MillingStrategyConfig,
)
from fibsem.structures import field_meta


@dataclass
class ExamplePluginMillingStrategyConfig(MillingStrategyConfig):
    """User-editable settings for the strategy.

    Rendered as a form under the strategy dropdown, using the same field
    metadata conventions as a pattern. Serialised into the protocol yaml, so
    keep the fields to plain types that round-trip through yaml.
    """

    # `type` is not optional for numbers: the strategy widget picks an integer
    # spinbox on `type is int` and falls through to a float spinbox otherwise,
    # so an int field without it renders as "3.00".
    #
    # All three forms read the same vocabulary, so this is spelled exactly as it
    # is in tasks.py and patterns.py.
    passes: int = field(
        default=3,
        metadata=field_meta(
            label="Passes",
            type=int,
            minimum=1,
            maximum=100,
            step=1,
            tooltip="Number of times to mill the pattern set.",
        ),
    )


class ExamplePluginMillingStrategy(MillingStrategy[ExamplePluginMillingStrategyConfig]):
    """Mill the stage's patterns `passes` times in sequence."""

    # `name` is the value stored in the protocol yaml and shown in the
    # dropdown; `fullname` is the longer label used where there is room.
    name: str = "Example Plugin"
    fullname: str = "Example Plugin Milling"

    # The base class instantiates this for you when no config is supplied, and
    # uses it to deserialise the config out of a protocol yaml.
    config_class = ExamplePluginMillingStrategyConfig

    def run(
        self,
        microscope: FibsemMicroscope,
        stage: FibsemMillingStage,
        asynch: bool = False,
        parent_ui=None,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        """Execute the milling stage.

        Keep this signature exactly as-is -- fibsemOS calls it positionally in
        some paths and by keyword in others.

        Cancellation is cooperative. The Stop button sets `stop_event`; nothing
        force-kills the thread. A strategy that never checks it cannot be
        stopped, so call `raise_if_cancelled(stop_event)` at every point where
        stopping is safe -- here, between passes and before the beam starts.
        """
        logging.info(
            "Running %s milling strategy for %s (%d passes)",
            self.name,
            stage.name,
            self.config.passes,
        )

        for i in range(self.config.passes):
            raise_if_cancelled(stop_event)

            logging.info("Pass %d/%d for %s", i + 1, self.config.passes, stage.name)

            # setup_milling applies the stage's milling settings (current,
            # voltage, dwell time, ...) to the microscope.
            setup_milling(microscope, milling_stage=stage, stop_event=stop_event)

            # define_patterns() calls your pattern's define() and converts the
            # result into the microscope's own pattern objects.
            microscope.draw_patterns(stage.define_patterns())

            raise_if_cancelled(stop_event)  # last chance before the beam starts

            # asynch=False so each pass finishes before the next begins. A
            # strategy that loops must not run asynchronously.
            microscope.run_milling(
                milling_current=stage.milling.milling_current,
                milling_voltage=stage.milling.milling_voltage,
                asynch=False,
            )
