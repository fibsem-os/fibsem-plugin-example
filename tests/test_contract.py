"""The contract between this plugin and fibsemOS.

These tests assert that each of the three classes actually *resolves through
fibsemOS's own registries* -- not merely that the package imports. Importing
proves nothing: a plugin with a typo in its entry point group imports fine and
is never loaded by anything.

CI runs this against fibsemOS `main`, so if a change upstream breaks the plugin
contract it fails here rather than silently, months later, on a user's
microscope.
"""

import pytest

PATTERN_NAME = "Example Plugin"
STRATEGY_NAME = "Example Plugin"
TASK_TYPE = "EXAMPLE_AUTOLAMELLA_TASK"


# ---------------------------------------------------------------------------
# The entry point groups themselves
# ---------------------------------------------------------------------------

def test_entry_point_groups_are_spelled_correctly():
    """Guard the failure mode with no symptoms.

    Nothing in fibsemOS scans for near-miss group names, so a plugin declared
    under "fibsem.stratagies" produces no error, no warning and no log line --
    it just never loads. These three strings are the only ones that work.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:  # Python < 3.10
        from importlib_metadata import entry_points

    declared = {
        group: {ep.name for ep in entry_points(group=group)}
        for group in ("fibsem.patterns", "fibsem.strategies", "fibsem.tasks")
    }

    assert "example_plugin_pattern" in declared["fibsem.patterns"]
    assert "example_plugin_strategy" in declared["fibsem.strategies"]
    assert "example_autolamella_task" in declared["fibsem.tasks"]


# ---------------------------------------------------------------------------
# Pattern
# ---------------------------------------------------------------------------

def test_pattern_resolves_through_the_registry():
    from fibsem.milling.patterning import get_pattern, get_pattern_names, get_patterns

    assert PATTERN_NAME in get_patterns(), sorted(get_patterns())
    assert PATTERN_NAME in get_pattern_names()

    pattern = get_pattern(PATTERN_NAME, {"length": 30.0e-6})
    assert pattern.length == 30.0e-6


def test_pattern_defines_shapes():
    from fibsem.milling.patterning import get_pattern

    shapes = get_pattern(PATTERN_NAME).define()
    assert len(shapes) == 2, shapes
    assert all(s.depth > 0 for s in shapes)


def test_distance_fields_declare_a_scale():
    """Catch the form that renders "0.000 m".

    Distances are stored in metres. The widget multiplies by `scale` for
    display, and `scale` defaults to None -> a scale of 1, so a correct 20 um
    default shows up as 0.000 m: right value, empty-looking form. Spreading
    DEFAULT_DISTANCE_METADATA is what avoids it.
    """
    from fibsem.milling.patterning import get_pattern

    metadata = get_pattern(PATTERN_NAME).field_metadata

    for name in ("length", "thickness", "depth"):
        assert metadata[name]["unit"] == "m", name
        assert metadata[name]["scale"] == 1e6, (
            f"{name} is a distance with no display scale: the form will show "
            "0.000 m. Spread DEFAULT_DISTANCE_METADATA into its metadata."
        )
        assert metadata[name]["decimals"] is not None, name


def test_numeric_strategy_fields_declare_their_type():
    """The strategy form picks an integer spinbox on `type is int` and falls
    through to a float spinbox otherwise, so an int without it renders 3.00."""
    from fibsem.milling.base import get_strategy

    metadata = get_strategy(STRATEGY_NAME).config.field_metadata
    assert metadata["passes"]["type"] is int


def test_pattern_defaults_are_sane_once_scaled():
    """The values behind the form: what the user sees is value * scale."""
    from fibsem.milling.patterning import get_pattern

    pattern = get_pattern(PATTERN_NAME)
    metadata = pattern.field_metadata

    for name, expected_display in (("length", 20.0), ("thickness", 2.0), ("depth", 1.0)):
        displayed = getattr(pattern, name) * metadata[name]["scale"]
        assert displayed == pytest.approx(expected_display), name
        # and inside the spinbox range, or the widget clamps it on open
        assert metadata[name]["minimum"] <= displayed <= metadata[name]["maximum"], name


def test_pattern_round_trips_through_a_protocol_dict():
    """A pattern that cannot survive to_dict/from_dict cannot be saved in a
    protocol yaml, so it works in the UI and vanishes on reload."""
    from fibsem.milling.patterning import get_pattern

    pattern = get_pattern(PATTERN_NAME, {"length": 25.0e-6, "thickness": 3.0e-6})
    ddict = pattern.to_dict()
    assert ddict["name"] == PATTERN_NAME

    restored = get_pattern(ddict["name"], ddict)
    assert restored.length == pattern.length
    assert restored.thickness == pattern.thickness


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

def test_strategy_resolves_through_the_registry():
    from fibsem.milling.base import get_strategy
    from fibsem.milling.strategy import get_strategies, get_strategy_names

    assert STRATEGY_NAME in get_strategies(), sorted(get_strategies())
    assert STRATEGY_NAME in get_strategy_names()

    strategy = get_strategy(STRATEGY_NAME, {"config": {"passes": 5}})
    assert strategy.config.passes == 5


def test_strategy_round_trips_through_a_protocol_dict():
    from fibsem.milling.base import get_strategy

    strategy = get_strategy(STRATEGY_NAME, {"config": {"passes": 4}})
    ddict = strategy.to_dict()

    assert ddict["name"] == STRATEGY_NAME
    assert get_strategy(ddict["name"], ddict).config.passes == 4


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

def test_task_resolves_through_the_registry():
    from fibsem.applications.autolamella.workflows.tasks import (
        get_task_config,
        get_task_names,
        get_tasks,
    )

    assert TASK_TYPE in get_tasks(), sorted(get_tasks())
    assert TASK_TYPE in get_task_names()

    config_cls = get_task_config(TASK_TYPE)
    assert config_cls.display_name == "Example AutoLamella Task"


def test_task_survives_protocol_load():
    """The path a protocol yaml actually takes.

    load_task_config() *skips* task types it does not recognise, with only a
    log warning -- the task disappears from the protocol and re-saving drops it
    from the yaml. This asserts the plugin task is not one of them.
    """
    from fibsem.applications.autolamella.workflows.tasks import load_task_config

    loaded = load_task_config(
        {
            "My Example Task": {
                "task_type": TASK_TYPE,
                "parameters": {"field_of_view": 60.0e-6, "note": "hello"},
            }
        }
    )

    assert "My Example Task" in loaded, dict(loaded)
    config = loaded["My Example Task"]
    assert config.field_of_view == 60.0e-6
    assert config.note == "hello"
    assert config.task_name == "My Example Task"


def test_task_overrides_run_correctly():
    """`run()` is the lifecycle wrapper; overriding it silently loses task
    state, history and hooks. Assert we implemented `_run()` instead."""
    from fibsem.applications.autolamella.workflows.tasks.base import AutoLamellaTask

    from fibsem_plugin_example.tasks import ExampleAutoLamellaTask

    assert "_run" in vars(ExampleAutoLamellaTask)
    assert ExampleAutoLamellaTask.run is AutoLamellaTask.run


# ---------------------------------------------------------------------------
# All three together
# ---------------------------------------------------------------------------

def test_milling_stage_built_from_yaml_uses_both_plugin_classes():
    """The end-to-end shape: a protocol yaml naming the plugin pattern and the
    plugin strategy produces a runnable milling stage."""
    from fibsem.milling.base import FibsemMillingStage

    stage = FibsemMillingStage.from_dict(
        {
            "name": "Example Plugin Stage",
            "milling": {},
            "pattern": {"name": PATTERN_NAME, "length": 25.0e-6},
            "strategy": {"name": STRATEGY_NAME, "config": {"passes": 2}},
        }
    )

    assert stage.pattern.name == PATTERN_NAME
    assert stage.strategy.name == STRATEGY_NAME
    assert stage.strategy.config.passes == 2

    ddict = stage.to_dict()
    assert ddict["pattern"]["name"] == PATTERN_NAME
    assert ddict["strategy"]["name"] == STRATEGY_NAME


# ---------------------------------------------------------------------------
# Import hygiene
# ---------------------------------------------------------------------------

def _module_imports(module_name):
    """Every `from X import ...` at any level of a module, as dotted strings."""
    import ast
    import importlib.util

    spec = importlib.util.find_spec(module_name)
    assert spec is not None and spec.origin is not None, module_name

    with open(spec.origin) as f:
        tree = ast.parse(f.read())

    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }


@pytest.mark.parametrize(
    "module",
    ["fibsem_plugin_example.patterns",
     "fibsem_plugin_example.strategies",
     "fibsem_plugin_example.tasks"],
)
def test_modules_do_not_import_the_patterning_package(module):
    """`fibsem/milling/patterning/__init__.py` builds a module-level snapshot by
    calling get_patterns(), so plugins are imported while that package is only
    half-initialised. Importing a name defined after that snapshot raises, the
    loader swallows it, and the plugin never registers -- visible only as an
    ERROR in the log file.

    Import from `fibsem.milling.patterning.patterns2` instead, which is fully
    imported by then.
    """
    offenders = {m for m in _module_imports(module) if m == "fibsem.milling.patterning"}
    assert not offenders, (
        f"{module} imports from the `fibsem.milling.patterning` package. "
        "Import from `fibsem.milling.patterning.patterns2` instead."
    )


def test_pattern_module_does_not_reach_fibsem_milling_base():
    """Why the pattern, strategy and task live in separate modules.

    `fibsem/milling/base.py` imports `fibsem.milling.patterning`, whose
    __init__ ends by calling get_patterns(). So a pattern plugin is imported
    while `fibsem.milling.base` is only *partially* initialised. Anything the
    pattern module imports that reaches back into `fibsem.milling.base` --
    including `fibsem.milling.tasks` and everything under `fibsem.applications`
    -- raises ImportError, the loader swallows it, and the pattern never
    registers.

    Strategies and tasks have no such restriction: their registries are built
    later, once fibsem is fully imported. Merging all three into one module is
    therefore the one refactor that quietly breaks the pattern.
    """
    forbidden_prefixes = ("fibsem.milling.base", "fibsem.milling.tasks", "fibsem.applications")

    offenders = sorted(
        m for m in _module_imports("fibsem_plugin_example.patterns")
        if m.startswith(forbidden_prefixes)
    )
    assert not offenders, (
        "The pattern module reaches fibsem.milling.base via "
        f"{offenders}. The pattern registry is built while that module is still "
        "initialising, so the pattern will silently fail to register. Keep "
        "patterns in their own module, importing only patterns2 and "
        "fibsem.structures."
    )
