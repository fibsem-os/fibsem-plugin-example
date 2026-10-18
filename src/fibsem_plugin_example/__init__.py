"""An example fibsemOS plugin.

One module for each of fibsemOS's extension points:

    patterns.py    ExamplePluginPattern          -> fibsem.milling.patterns
    strategies.py  ExamplePluginMillingStrategy  -> fibsem.milling.strategies
    tasks.py       ExampleAutoLamellaTask        -> fibsem.autolamella.tasks
    scanner/       driver() (a scan generator)   -> fibsem.drivers

They are wired up in pyproject.toml. Nothing imports them from here -- fibsemOS
loads each one directly from its entry point.
"""

__version__ = "0.1.0"
