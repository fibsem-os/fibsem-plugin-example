# fibsemOS plugin example

A working [fibsemOS](https://github.com/fibsem-os/fibsem-os) plugin, in one package, covering all three extension points:

| File | Class | Extends fibsemOS with |
|---|---|---|
| [`patterns.py`](src/fibsem_plugin_example/patterns.py) | `ExamplePluginPattern` | a milling pattern — a crosshair marker |
| [`strategies.py`](src/fibsem_plugin_example/strategies.py) | `ExamplePluginMillingStrategy` | a milling strategy — mill in N passes |
| [`tasks.py`](src/fibsem_plugin_example/tasks.py) | `ExampleAutoLamellaTask` | an AutoLamella workflow task |

Everything that makes them plugins is in [`pyproject.toml`](pyproject.toml) — three `[project.entry-points]` tables, nothing else. No changes to fibsemOS, no registration calls, no files to edit in the fibsem tree.

Real lab plugins usually register several things at once, which is why this is one package rather than three.

## Start here

Click **Use this template** on GitHub, then:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-PLUGIN.git
cd YOUR-PLUGIN
pip install -e ".[test]"
```

Install it into the **same environment as fibsemOS** — that is how the app finds it.

Then check that fibsemOS can see all three:

```bash
python -c "
from fibsem.milling.patterning import get_patterns
from fibsem.milling.strategy import get_strategies
from fibsem.applications.autolamella.workflows.tasks import get_tasks
print('pattern :', 'Example Plugin' in get_patterns())
print('strategy:', 'Example Plugin' in get_strategies())
print('task    :', 'EXAMPLE_AUTOLAMELLA_TASK' in get_tasks())
"
```

Three `True`s means it worked. Any `False` — see [When nothing shows up](#when-nothing-shows-up).

You can also just run the tests, which check the same thing more thoroughly:

```bash
pytest
```

Then open AutoLamella: the pattern and strategy appear in the milling widget dropdowns, and the task appears in the task picker.

## Making it yours

1. Rename the package directory `src/fibsem_plugin_example/` and update `name` and the three entry point values in `pyproject.toml` to match.
2. Change the `name` on the pattern and strategy, and `task_type` / `display_name` on the task config. These are what users see and what protocol files refer to — pick them once and keep them stable.
3. Replace the bodies of `define()`, `run()` and `_run()`.
4. Re-run `pip install -e .` — see the reinstall note below.
5. Update `tests/test_contract.py` with your names. Keep the tests: they are what tells you fibsemOS changed under you.

## When nothing shows up

Plugins that fail to load do so **quietly** — the app starts normally and your class is simply absent. In rough order of likelihood:

**You edited `pyproject.toml` and didn't reinstall.** Entry points are baked into the installed metadata, not read from your source tree. Editing `pyproject.toml` does nothing until you `pip install -e .` again. Editing your *Python* files is fine — `-e` picks those up.

**Your fibsemOS is too old.** All three modules import `field_meta` from `fibsem.structures`, added in fibsemOS 0.5.2, and against anything older every entry point raises `ImportError` — all three swallowed by the loader. `pip install` now refuses the too-old combination outright rather than letting it happen quietly, but an environment assembled before that can still be in this state. Check with `python -c "from fibsem.structures import field_meta"`, and see [Requirements](#requirements).

**The entry point group name has a typo.** It must be exactly `fibsem.patterns`, `fibsem.strategies` or `fibsem.tasks`. Nothing scans for near-misses, so `fibsem.stratagies` produces no error, no warning and no log line — it just never loads. `test_entry_point_groups_are_spelled_correctly` catches this.

**Your pattern module imports too much.** Pattern plugins are loaded at a delicate moment and have two import restrictions the other two don't — see [Why three modules](#why-three-modules) below. If your pattern is the thing that went missing, look there first.

**The name collides with a built-in.** Built-ins win name clashes and yours is shadowed with no message. Check `get_pattern_names()` / `get_strategy_names()` / `get_task_names()` for what is already taken.

**It's installed in a different environment.** `pip -V` and `python -c "import fibsem; print(fibsem.__file__)"` should point at the same place.

Failures that do get logged appear as `ERROR Unexpected error raised while attempting to import ... from '<your entry point>'`, with a traceback — worth checking the log file before anything else.

## Why three modules

Not tidiness — merging them breaks the pattern.

`fibsem/milling/base.py` imports `fibsem.milling.patterning`, and that package's `__init__` ends with a module-level `MILLING_PATTERNS = get_patterns()`. So **pattern plugins are imported while `fibsem.milling.base` is only partially initialised**, which puts two restrictions on the pattern module and only the pattern module:

- Import `BasePattern` from `fibsem.milling.patterning.patterns2`, never from the `fibsem.milling.patterning` package — names defined after that snapshot (`MILLING_PATTERNS`, `MILLING_PATTERN_NAMES`, `PROTOCOL_MILL_MAP`) don't exist yet.
- Import nothing that reaches back into `fibsem.milling.base` — that includes `fibsem.milling.tasks` and **everything under `fibsem.applications`**. Putting your pattern in the same file as your task is enough to trip this, because the task needs `AutoLamellaTaskConfig`.

Either one raises `ImportError`, the plugin loader catches it, and the pattern silently never registers. Strategies and tasks have no such restriction: their registries are built later, once fibsem is fully imported.

`test_pattern_module_does_not_reach_fibsem_milling_base` and `test_modules_do_not_import_the_patterning_package` keep this from drifting. Leave them in.

## Form metadata: the "0.000 m" trap

Distances are stored in **metres**, and the forms scale them for display. If you leave `scale` off a distance field, the widget falls back to a scale of 1 and a perfectly correct `20e-6` default renders as **`0.000 m`** — an empty-looking form with nothing actually wrong behind it. This is the easiest way to ship a plugin that looks broken.

For patterns and strategies, spread `DEFAULT_DISTANCE_METADATA` (from `fibsem.milling.properties`) into the field, exactly as the built-in patterns do. It carries `scale`, `unit`, `minimum`, `maximum`, `step` and `decimals` together.

The three forms are built by different widgets that read **different metadata keys**, which is worth knowing before you copy metadata between them:

| | Pattern form | Strategy form | Task parameters form |
|---|---|---|---|
| unit key | `unit` | `unit` | `units` |
| scale | `scale` | `scale` | `scale` |
| help text | `tooltip` | `tooltip` | `help` |
| numeric type | inferred | **`type` required** for `int` | inferred |

Getting one wrong is never an error — just a form that looks wrong. `test_distance_fields_declare_a_scale`, `test_numeric_strategy_fields_declare_their_type` and `test_pattern_defaults_are_sane_once_scaled` cover the cases in this repo; extend them as you add fields.

## Gotchas worth knowing before you write much

**Override `_run()`, not `run()`.** On an `AutoLamellaTask`, `run()` is the lifecycle wrapper: it calls `pre_task()`, fires the task hooks, calls `_run()`, then calls `post_task()`. Overriding `run()` is the obvious guess and silently loses the task's state, its history entry and every hook — with no error anywhere.

**Cancellation is cooperative.** The Stop button sets an event; nothing force-kills the thread. A strategy that never checks `stop_event`, or a task that never calls `self._check_for_abort()`, cannot be stopped. Check at every point where stopping is safe.

**`task_type` is forever.** It is the identifier written into protocol files. Renaming it orphans every existing protocol — and unregistered task types are *dropped* on load with only a log warning, so the task disappears from the yaml the next time it is saved.

**Config classes must round-trip through yaml.** Patterns and strategy configs are serialised into the protocol. Stick to plain types, and let the tests here check `to_dict`/`from_dict` for you.

**Write images under `lamella.path`.** Anywhere else and they are lost when the experiment is copied off the microscope.

## Sharing it

Because it is a normal Python package, another lab installs it the same way you do:

```bash
pip install git+https://github.com/YOUR-USERNAME/YOUR-PLUGIN.git
```

That is enough — the entry points are in the wheel, so the plugin is live the next time fibsemOS starts. Nothing needs to be configured in the app.

Two things make that pleasant for the person on the other end:

- **Tag your releases.** `pip install git+https://.../YOUR-PLUGIN.git@v1.0` pins them to something reproducible, which matters when the plugin drives a beam.
- **Keep the CI.** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) installs against fibsemOS `main` on every change and weekly on a schedule. It costs nothing and it means *you* find out when an upstream change breaks the plugin — rather than a collaborator, mid-session, with a red herring of an error message.

If your plugin is broadly useful, [open an issue](https://github.com/fibsem-os/fibsem-os/issues) — some of these belong in fibsemOS itself.

## Requirements

fibsemOS 0.5.2 or newer, and Python 3.9+. The plugin contract does not need the `[ui]` extra: all three registries resolve without napari or PyQt5, which is why the CI here runs with no Qt and no virtual display.

That floor is load-bearing, not caution. All three modules import `field_meta` from `fibsem.structures`, which arrived in 0.5.2 — against anything older, every entry point raises `ImportError` and the loader swallows all three.

**At the time of writing the newest fibsemOS on PyPI is 0.5.1**, so `pip install fibsem` is not yet enough. Install fibsemOS from `main` until 0.5.2 is released:

```bash
pip install "fibsem @ git+https://github.com/fibsem-os/fibsem-os.git@main"
```

## License

MIT — see [LICENSE](LICENSE). Change it to whatever suits your lab.
