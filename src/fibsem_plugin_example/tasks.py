"""An example AutoLamella task.

A task is one step of the AutoLamella workflow, run once per lamella. This one
moves to the lamella's milling pose, optionally pauses for the operator, and
acquires a reference image at a configurable field of view -- a tour of the
helpers on the base class rather than anything clever. Replace the body of
`_run()` with your own work.

Registered as a `fibsem.tasks` entry point in pyproject.toml. Once installed it
appears in the task picker when building a protocol.
"""

import logging
from dataclasses import dataclass, field
from typing import ClassVar, Type

from fibsem.applications.autolamella.structures import AutoLamellaTaskConfig
from fibsem.applications.autolamella.workflows.tasks.base import AutoLamellaTask
from fibsem.applications.autolamella.workflows.ui import ask_user
from fibsem.structures import field_meta


@dataclass
class ExampleAutoLamellaTaskConfig(AutoLamellaTaskConfig):
    """The task's protocol entry.

    Subclass fields become the task's `parameters` block in the protocol yaml
    and are rendered as a form in the task config widget. The base class
    already provides `milling`, `reference_imaging` and `task_name`.
    """

    # `task_type` is the identifier stored in the protocol yaml. It must be
    # unique and it must be stable: renaming it orphans every protocol that
    # already refers to the old value. (Unregistered task types are dropped
    # from a protocol on load, so an orphaned task disappears from the yaml
    # the next time it is saved.)
    task_type: ClassVar[str] = "EXAMPLE_AUTOLAMELLA_TASK"

    # What the user sees in the task picker and the workflow queue.
    display_name: ClassVar[str] = "Example AutoLamella Task"

    # Every config form -- tasks, patterns and strategies alike -- reads one
    # vocabulary, defined by DEFAULT_FIELD_METADATA in fibsem.structures.
    # `field_meta` is that vocabulary as keyword arguments, so a misspelled key
    # is a TypeError when your plugin is imported.
    #
    # A plain `metadata={...}` dict still works, and is all the older examples
    # you may run into use. It is worth preferring `field_meta` anyway, because
    # a mistyped key in a dict is completely silent: the form renders, the value
    # is right, and the label or the unit suffix is just missing. (An unscaled
    # distance renders as "0.00", because the stored value is in metres --
    # scale=1e6 gives a micron spinbox with a "um" suffix.)
    field_of_view: float = field(
        default=80.0e-6,
        metadata=field_meta(
            label="Field of View",
            unit="m",
            scale=1e6,
            tooltip="Horizontal field width for the reference image.",
        ),
    )
    note: str = field(
        default="",
        metadata=field_meta(tooltip="Free-text note written to the log for this lamella."),
    )


class ExampleAutoLamellaTask(AutoLamellaTask):
    """Acquire a reference image for one lamella."""

    # Both are needed: `config` for type checkers, `config_cls` for fibsemOS.
    # `config_cls` is how the plugin loader finds your task_type, so a task
    # without it fails to register.
    config: ExampleAutoLamellaTaskConfig
    config_cls: ClassVar[Type[ExampleAutoLamellaTaskConfig]] = ExampleAutoLamellaTaskConfig

    def _run(self) -> None:
        """Do the work.

        Override `_run()`, never `run()`. `run()` is the lifecycle wrapper: it
        calls pre_task(), fires the task hooks, calls `_run()`, then calls
        post_task(). Overriding `run()` looks like the obvious thing to do and
        silently loses the task's state, its history entry and every hook --
        with no error at any point.

        Anything raised here is recorded as a task failure, which is what you
        want; there is no need to catch and swallow.
        """
        # Move the stage to this lamella's milling pose. Raises if the pose was
        # never set, which is the correct behaviour -- do not guess a position.
        self._move_to_milling_pose()

        # `self.validate` is True when the operator has ticked "supervise" for
        # this task in the protocol. Gate every prompt on it, or the task
        # blocks forever in an unattended run.
        if self.validate:
            ask_user(
                self.parent_ui,
                msg=f"Example task for {self.lamella.name}. Press Continue when ready.",
                pos="Continue",
            )

        # Long or looping work should call self._check_for_abort() regularly so
        # the Stop button can interrupt it. The helpers below already do.
        self._check_for_abort()

        # log_status_message drives the status bar and the per-task step shown
        # in the UI. The first argument is the machine-readable step name that
        # ends up in the log; the second is what the operator reads.
        self.log_status_message("EXAMPLE_STEP", "Acquiring example reference image...")

        # Images must be written under the lamella's own directory, or they are
        # lost when the experiment is moved or copied off the microscope.
        image_settings = self.config.imaging
        image_settings.path = self.lamella.path

        # Acquires SEM and/or FIB according to the task's reference_imaging
        # settings, updates the UI, and records the written paths on the task
        # record so they can be found again later.
        self._acquire_channels(
            image_settings=image_settings,
            filename=f"ref_{self.task_name}",
            field_of_view=self.config.field_of_view,
        )

        if self.config.note:
            logging.info("%s: %s", self.lamella.name, self.config.note)
