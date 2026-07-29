"""An example fibsemOS plugin.

Three modules, one for each of fibsemOS's extension points:

    patterns.py    ExamplePluginPattern          -> fibsem.patterns
    strategies.py  ExamplePluginMillingStrategy  -> fibsem.strategies
    tasks.py       ExampleAutoLamellaTask        -> fibsem.tasks

They are wired up in pyproject.toml. Nothing imports them from here -- fibsemOS
loads each one directly from its entry point.
"""

__version__ = "0.1.0"
