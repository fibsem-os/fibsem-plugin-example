# fibsemOS plugin example

A working [fibsemOS](https://github.com/fibsem-os/fibsem-os) plugin, in one package, covering all four extension points:

| File | Class | Extends fibsemOS with |
|---|---|---|
| [`patterns.py`](src/fibsem_plugin_example/patterns.py) | `ExamplePluginPattern` | a milling pattern — a crosshair marker |
| [`strategies.py`](src/fibsem_plugin_example/strategies.py) | `ExamplePluginMillingStrategy` | a milling strategy — mill in N passes |
| [`tasks.py`](src/fibsem_plugin_example/tasks.py) | `ExampleAutoLamellaTask` | an AutoLamella workflow task |
| [`scanner/`](src/fibsem_plugin_example/scanner) | `driver()` | a device driver — a simulated external scan generator |
| [`knife/`](src/fibsem_plugin_example/knife) | `driver()` | a device driver — a new device type with commands |
| [`lamp/`](src/fibsem_plugin_example/lamp) | `driver()` | a device driver — the smallest one, a new device type with settings only |

Everything that makes them plugins is in [`pyproject.toml`](pyproject.toml) — its `[project.entry-points]` tables, nothing else. No changes to fibsemOS, no registration calls, no files to edit in the fibsem tree.

Real lab plugins usually register several things at once, which is why this is one package rather than four.

## Start here

Click **Use this template** on GitHub, then:

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-PLUGIN.git
cd YOUR-PLUGIN
pip install -e ".[test]"
```

Install it into the **same environment as fibsemOS** — that is how the app finds it.

Then check that fibsemOS can see them:

```bash
python -c "
from fibsem.milling.patterning import get_patterns
from fibsem.milling.strategy import get_strategies
from fibsem.applications.autolamella.workflows.tasks import get_tasks
print('pattern :', 'Example Plugin' in get_patterns())
print('strategy:', 'Example Plugin' in get_strategies())
print('task    :', 'EXAMPLE_AUTOLAMELLA_TASK' in get_tasks())
from fibsem.drivers.registry import get_driver
print('drivers :', 'scan_generator' in get_driver('FakeScan').devices,
      'knife' in get_driver('KnifeCo').devices, 'lamp' in get_driver('LampCo').devices)
"
```

All `True` means it worked. Any `False` — see [When nothing shows up](#when-nothing-shows-up).

You can also just run the tests, which check the same thing more thoroughly:

```bash
pytest
```

Then open AutoLamella: the pattern and strategy appear in the milling widget dropdowns, and the task appears in the task picker.

## Making it yours

1. Rename the package directory `src/fibsem_plugin_example/` and update `name` and the entry point values in `pyproject.toml` to match. Delete what you don't need, along with its entry point and tests: most plugins have no device drivers, and one that adds a device needs only the example closest to it.
2. Change the `name` on the pattern and strategy, and `task_type` / `display_name` on the task config. These are what users see and what protocol files refer to — pick them once and keep them stable.
3. Replace the bodies of `define()`, `run()` and `_run()`.
4. Re-run `pip install -e .` — see the reinstall note below.
5. Update `tests/test_contract.py` with your names. Keep the tests: they are what tells you fibsemOS changed under you.

## When nothing shows up

Plugins that fail to load do so **quietly** — the app starts normally and your class is simply absent. In rough order of likelihood:

**You edited `pyproject.toml` and didn't reinstall.** Entry points are baked into the installed metadata, not read from your source tree. Editing `pyproject.toml` does nothing until you `pip install -e .` again. Editing your *Python* files is fine — `-e` picks those up.

**Your fibsemOS is too old.** Every module declares their fields in fibsemOS 0.6's metadata vocabulary (`Display`, `param` and `distance_param`, in `fibsem.structures.params`), and against anything older every entry point fails at import, each one swallowed by the loader. `pip install` refuses the too-old combination outright, but an environment assembled before that can still be in this state. Check with `python -c "from fibsem.structures.params import Display, distance_param, param"`, and see [Requirements](#requirements).

**The entry point group name has a typo.** It must be exactly `fibsem.milling.patterns`, `fibsem.milling.strategies`, `fibsem.autolamella.tasks`, `fibsem.grid.tasks` or `fibsem.drivers`. Nothing scans for near-misses, so `fibsem.milling.stratagies` produces no error, no warning and no log line — it just never loads. `test_entry_point_groups_are_spelled_correctly` catches this.

**The name collides with a built-in.** Built-ins win name clashes and yours is shadowed with no message. Check `get_pattern_names()` / `get_strategy_names()` / `get_tasks()` for what is already taken.

**It's installed in a different environment.** `pip -V` and `python -c "import fibsem; print(fibsem.__file__)"` should point at the same place.

Failures that do get logged appear as `ERROR Unexpected error raised while attempting to import ... from '<your entry point>'`, with a traceback — worth checking the log file before anything else.

## Adding a device

A device driver builds devices for the microscope from its configuration file. Three examples, each a working driver on this computer, cover the usual cases:

| Your device | Start from | Shows |
|---|---|---|
| One your microscope's own driver already builds (a beam, the stage, the manipulator) | no code: an entry in the configuration, below | `enabled`, `required`, the device's own keys |
| A new kind of device with settings only | [`lamp/`](src/fibsem_plugin_example/lamp) | the least a driver needs: a device class, its builder, the record |
| A new kind of device with commands | [`knife/`](src/fibsem_plugin_example/knife) | commands, limits the unit reports, a fault when its controller is offline, a hardware check step, the guided setup, closing its connection |
| A type fibsemOS already has, on its own controller (here a scan generator; another type follows the same pattern) | [`scanner/`](src/fibsem_plugin_example/scanner) | implementing fibsemOS's interface for that type, filling a beam's role, one connection shared by several entries |

[`examples/devices-configuration.yaml`](examples/devices-configuration.yaml) adds all three to the Demo microscope, so you can try them with no hardware:

```python
from fibsem import utils

microscope, settings = utils.setup_session(config_path="examples/devices-configuration.yaml")
knife = microscope.devices["knife"]
knife.speed.set_value(2e-4)
knife.cut()
```

### Step by step

1. **Wrap the vendor's library.** Each example has a stand-in for it (`sdk.py`, or `LampController` in the lamp's `devices.py`) that knows nothing about fibsem. Yours is the real library.
2. **Write the device class** (`devices.py`): a `Device` subclass declaring each `DeviceParameter` with its type, SI unit, limits and `Display`. For each parameter write `read_<name>()`, and `write_<name>(value)` if it can be set; without a `write_`, it is read-only. A command is a method marked `@command`. Turn the library's errors into `DeviceFault(message, device=self.name)`.
3. **Write the builder** (in `devices.py`): a function taking the configuration entry and the build context, returning the connected device. Its keys are in `entry.options`.
4. **Write the record** (`__init__.py`): `driver()` returns a `DriverEntry` naming the maker and, for each device type, its builder by import path. Keep this module free of other imports.
5. **Register the entry point** in `pyproject.toml`, under `[project.entry-points."fibsem.drivers"]`, and run `pip install -e .` again.
6. **Optional: offer it in the guided setup** (`setup.py`): a `SetupDevice` with its keys and their defaults. It also checks an entry's keys, so a misspelled key fails the connect instead of being ignored.
7. **Add it to the microscope's configuration**, as an entry under `hardware.devices`:

   ```yaml
   hardware:
     devices:
       - name: knife          # its name in microscope.devices
         type: knife          # the device type, as the driver's record names it
         driver: KnifeCo      # the driver's maker name
         address: 127.0.0.1   # every other key is the driver's own
   ```

   The list is an overlay on what the microscope's own driver builds: an entry naming a device it already has (`- name: manipulator` with `enabled: false`) changes that one, and anything else is added. A device the file lists must build, or the connect fails; `required: false` connects without it.
8. **Check it.** Connect with the configuration. The device shows in the configuration window's Instrument and Devices tabs, `fibsem-cli hardware-check` runs its steps, and the App Server serves it at `/microscope/devices/<name>`, which is how the web app and the agent reach it. [`tests/test_knife_and_lamp.py`](tests/test_knife_and_lamp.py) checks each of these.

### A device on another computer

A device whose controller is plugged into another computer is served from there by a device server, and the microscope's configuration names it with `driver: remote`. The scanner does this too ([`remote.py`](src/fibsem_plugin_example/scanner/remote.py)); skip it until you need it. [`tests/test_scanner.py`](tests/test_scanner.py) follows the scanner through every step, including the App Server and the device server.

fibsemOS's [devices guide](https://github.com/fibsem-os/fibsem-os/blob/main/docs/developers/devices.md#adding-a-driver) explains each part in full.

## Form metadata: the "0.000 m" trap

Distances are stored in **metres**, and the forms scale them for display. If you leave `scale` off a distance field, the widget falls back to a scale of 1 and a perfectly correct `20e-6` default renders as **`0.000 m`** — an empty-looking form with nothing actually wrong behind it. This is the easiest way to ship a plugin that looks broken.

Declare any distance with `distance_param(label, doc)` (from `fibsem.structures.params`), exactly as the built-in patterns do. It carries the unit (`"m"`), limits in metres, and a `Display` that shows microns with a sensible step and decimals.

Every form (pattern, strategy and task parameters) reads one vocabulary: each field declares a `Parameter` with `param(default, ...)`:

```python
from fibsem.structures.params import Display, RangeLimit, param

passes: int = param(
    3,
    limits=RangeLimit(1, 100),          # in the value's own unit (SI)
    doc="Number of times to mill.",     # the tooltip
    display=Display("Passes", step=1),  # label, scale, step, decimals
)
```

The value stays plain (`config.passes` is the int). The form reads the Parameter back as `config.params.passes`, and `describe()` gives the whole config as a JSON Schema.

The SI unit goes in `unit`, limits are in SI, and everything about how the form shows the value (its label, the `scale` that turns metres into microns, `step`, `decimals`) goes in the `Display`. The field's annotation gives its type, so an `int` field gets an integer spinbox. A misspelled keyword is a `TypeError` when your plugin is imported. `test_distance_fields_declare_a_scale`, `test_numeric_strategy_fields_declare_their_type` and `test_pattern_defaults_are_sane_once_scaled` cover the cases in this repo; extend them as you add fields.

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

fibsemOS 0.6 or newer, and Python 3.10+ (fibsemOS's own floor). The pattern, strategy and task need no extras. The device tests also check them in the application and its servers, so they need fibsemOS's `[ui]` and `[server]` extras and skip without them; CI installs both and runs Qt offscreen.

That floor is load-bearing, not caution. Every module declares their fields in fibsemOS 0.6's metadata vocabulary (`Display`, `param` and `distance_param`, in `fibsem.structures.params`). Against anything older, every entry point fails at import and the loader swallows each one.

**At the time of writing the newest fibsemOS on PyPI is 0.5.3**, so `pip install fibsem` is not yet enough. Install fibsemOS from `main` until 0.6 is released:

```bash
pip install "fibsem @ git+https://github.com/fibsem-os/fibsem-os.git@main"
```

## License

MIT — see [LICENSE](LICENSE). Change it to whatever suits your lab.
