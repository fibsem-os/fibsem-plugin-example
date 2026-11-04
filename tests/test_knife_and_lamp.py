"""The knife and the lamp, two new device types, through fibsemOS's plugin path, and
the example configuration that adds them and the scanner to the Demo microscope.

The App Server test needs fibsemOS's ``[server]`` extra, and skips without it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fibsem import utils
from fibsem.devices import DeviceFault, ParameterReadOnly
from fibsem.devices.entries import DeviceBuildError
from fibsem.drivers.registry import DRIVER_PLUGINS, get_driver
from fibsem.structures.settings import BeamType

from fibsem_plugin_example.knife.devices import Knife
from fibsem_plugin_example.lamp.devices import Lamp
from fibsem_plugin_example.scanner.devices import FakeScanner

EXAMPLE = Path(__file__).parent.parent / "examples" / "devices-configuration.yaml"


@pytest.fixture(autouse=True)
def _no_sim_delay(monkeypatch):
    monkeypatch.setenv("FIBSEM_SIM_NO_DELAY", "1")


def _connect(path):
    microscope, _ = utils.setup_session(setup_logging=False, config_path=str(path))
    return microscope


def _with(tmp_path, change):
    """The example configuration with *change* made to its knife entry."""
    config = yaml.safe_load(EXAMPLE.read_text())
    knife = next(e for e in config["hardware"]["devices"] if e["name"] == "knife")
    change(knife)
    path = tmp_path / "configuration.yaml"
    path.write_text(yaml.safe_dump(config))
    return path


@pytest.fixture
def microscope():
    microscope = _connect(EXAMPLE)
    yield microscope
    microscope.disconnect()


# -- discovery ----------------------------------------------------------------------


@pytest.mark.parametrize("name, type_", [("KnifeCo", "knife"), ("LampCo", "lamp")])
def test_the_entry_point_is_found_and_listed(name, type_):
    records = [r for r in DRIVER_PLUGINS.plugin_records() if r.name == name]
    assert len(records) == 1 and records[0].loaded
    assert set(get_driver(name).devices) == {type_}


def test_neither_is_offered_as_a_manufacturer():
    from fibsem.drivers.registry import registered_manufacturers

    assert not {"KnifeCo", "LampCo"} & set(registered_manufacturers())


def test_the_guided_setup_offers_the_knife_only():
    from fibsem.drivers.registry import device_setups

    from fibsem_plugin_example.knife.setup import KNIFE

    offered = [driver for driver, _ in device_setups()]
    assert ("KnifeCo", KNIFE) in device_setups()
    assert "LampCo" not in offered  # the lamp has no setup.py


# -- the example configuration ------------------------------------------------------


def test_the_example_builds_all_three_devices(microscope):
    assert isinstance(microscope.devices["fake_scanner"], FakeScanner)
    assert isinstance(microscope.devices["knife"], Knife)
    assert isinstance(microscope.devices["lamp"], Lamp)
    scanner = microscope.devices["fake_scanner"]
    assert microscope.beams[BeamType.ELECTRON].scanner is scanner


def test_an_unknown_knife_key_fails_the_build(tmp_path):
    with pytest.raises(DeviceBuildError, match="unknown keys"):
        _connect(_with(tmp_path, lambda e: e.update(sped=1e-4)))


def test_a_knife_with_no_address_fails_the_build(tmp_path):
    with pytest.raises(DeviceBuildError, match="no address"):
        _connect(_with(tmp_path, lambda e: e.update(address="")))


def test_disconnect_closes_the_knifes_connection(tmp_path):
    microscope = _connect(EXAMPLE)
    controller = microscope.devices["knife"]._controller
    microscope.disconnect()
    assert not controller.open


# -- parameters and commands --------------------------------------------------------


def test_the_lamp_clips_to_its_limits_and_counts_its_hours(microscope):
    lamp = microscope.devices["lamp"]
    lamp.on.set_value(True)
    lamp.brightness.set_value(2.0)
    assert lamp.brightness.get_value() == 1.0
    assert lamp.hours.get_value() >= 120.0
    with pytest.raises(ParameterReadOnly):
        lamp.hours.set_value(0.0)


def test_the_knife_angle_is_limited_by_what_the_unit_reports(microscope):
    knife = microscope.devices["knife"]
    assert knife.angle.metadata.limits.max == 0.5
    knife.angle.set_value(1.0)
    assert knife.angle.get_value() == 0.5


def test_the_knife_cuts_and_counts(microscope):
    knife = microscope.devices["knife"]
    assert knife.cut() == 1
    assert knife.cuts.get_value() == 1


def test_an_offline_controller_is_a_device_fault(microscope):
    knife = microscope.devices["knife"]
    knife._controller.close()  # the controller went away
    with pytest.raises(DeviceFault) as raised:
        knife.cut()
    assert raised.value.device == "knife"


def test_the_hardware_check_runs_the_knifes_own_steps(microscope):
    from fibsem.tools.hardware_check import Level, run_hardware_check

    speed = microscope.devices["knife"].speed.get_value()
    report = run_hardware_check(microscope, Level.SETTINGS)
    steps = {f.step: f for f in report.findings if f.device == "knife"}
    assert {"read angle", "set speed", "restore speed"} <= set(steps)
    assert all(f.result.value == "pass" for f in steps.values()), report.format()
    assert microscope.devices["knife"].speed.get_value() == speed
    assert microscope.devices["knife"].cuts.get_value() == 0  # a check never cuts


# -- the App Server (what the application and the agent reach) ----------------------


def test_the_app_server_serves_both(microscope):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from fibsem.server import AuthConfig, build_server

    app = build_server(microscope, auth=AuthConfig.generate(level="drive", token="t"))
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers.update({"Authorization": "Bearer t"})
        assert {"knife", "lamp"} <= set(client.get("/microscope/devices").json())
        r = client.put("/microscope/devices/lamp/brightness", json={"value": 0.25})
        assert r.json() == {"value": 0.25}
        r = client.post("/microscope/devices/knife/commands/cut", json={"kwargs": {}})
        assert r.json()["result"] == 1
        microscope.devices["knife"]._controller.close()
        r = client.post("/microscope/devices/knife/commands/cut", json={"kwargs": {}})
        assert r.status_code == 502  # the controller's refusal, naming the knife
