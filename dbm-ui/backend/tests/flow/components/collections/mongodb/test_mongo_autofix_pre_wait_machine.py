# -*- coding: utf-8 -*-
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.utils import timezone

from backend.flow.engine.bamboo.scene.mongodb.mongodb_autofix_pre import MongoAutofixPreFlow
from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_triage import MongoAutofixPreTriageComponent
from backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_wait_machine import (
    DEFAULT_MAX_WAIT_SEC,
    I_SERIES_MAX_WAIT_SEC,
    WAIT_FOREVER_SEC,
    MongoAutofixPreWaitMachineComponent,
    MongoAutofixPreWaitMachineService,
    _max_wait_seconds,
    _probe_uptime_once,
    resolve_max_wait_seconds,
    wait_gse_forever,
    wait_machine_act_name,
)


class FakeData:
    def __init__(self, kwargs):
        self.kwargs = kwargs
        self.outputs = SimpleNamespace()

    def get_one_of_inputs(self, key):
        return self.kwargs if key == "kwargs" else {}


def test_i_series_waits_30_minutes_case_insensitive():
    assert _max_wait_seconds("IT5.4XLARGE64") == I_SERIES_MAX_WAIT_SEC
    assert _max_wait_seconds("i6t.8xlarge112") == I_SERIES_MAX_WAIT_SEC


def test_other_device_class_waits_four_hours():
    assert _max_wait_seconds("SA5.MEDIUM4") == DEFAULT_MAX_WAIT_SEC
    assert _max_wait_seconds("") == DEFAULT_MAX_WAIT_SEC


def test_wait_act_name_high_io_and_standard():
    high = {"ip": "127.0.0.1"}
    std = {"ip": "127.0.0.2"}
    assert wait_machine_act_name(high, "IT5.4XLARGE64") == "等待机器启动-127.0.0.1-(高IO/30m/2m)"
    assert wait_machine_act_name(std, "SA5.MEDIUM4") == "等待机器启动-127.0.0.2-(标准类/4h/2m)"
    assert wait_machine_act_name(std, "") == "等待机器启动-127.0.0.2-(标准类/4h/2m)"


def test_mongos_waits_gse_forever():
    info = {"ip": "127.0.0.3", "wait_gse_forever": True, "machine_type": "mongos"}
    assert wait_gse_forever(info) is True
    assert resolve_max_wait_seconds(info, "IT5.4XLARGE64") == WAIT_FOREVER_SEC
    assert wait_machine_act_name(info, "IT5.4XLARGE64") == "等待机器启动-127.0.0.3-(mongos/一直等/2m)"


def test_mongos_never_times_out_wait_machine():
    service = MongoAutofixPreWaitMachineService()
    service.log_info = MagicMock()
    service.finish_schedule = MagicMock()
    data = FakeData({"ip": "127.0.0.1", "bk_cloud_id": 0, "wait_gse_forever": True})
    data.outputs.started_at = (timezone.now() - timedelta(hours=48)).isoformat()
    data.outputs.machine_started = 0
    data.outputs.max_wait_sec = WAIT_FOREVER_SEC
    data.outputs.poll_rounds = 2

    with patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_wait_machine._probe_uptime_once",
        return_value=False,
    ):
        assert service._schedule(data, None) is True

    assert getattr(data.outputs, "timed_out", 0) != 1
    service.finish_schedule.assert_not_called()


def test_uptime_probe_executes_uptime_script():
    with patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_wait_machine._probe_gse_alive_once",
        return_value=True,
    ) as probe:
        assert _probe_uptime_once("127.0.0.1", 0) is True

    probe.assert_called_once_with(
        "127.0.0.1",
        0,
        log_fn=None,
        script="uptime",
        task_name_prefix="mongo_autofix_pre_wait_uptime",
    )


def test_execute_sets_i_series_timeout_and_detects_started_machine():
    service = MongoAutofixPreWaitMachineService()
    service.log_info = MagicMock()
    data = FakeData({"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_host_id": 1})

    with patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_wait_machine._get_device_class",
        return_value="IT5.4XLARGE64",
    ), patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_wait_machine._probe_uptime_once",
        return_value=True,
    ):
        assert service._execute(data, None) is True

    assert data.outputs.max_wait_sec == I_SERIES_MAX_WAIT_SEC
    assert data.outputs.machine_started == 1
    assert data.outputs.poll_rounds == 1


def test_timeout_continues_to_triage():
    service = MongoAutofixPreWaitMachineService()
    service.log_warning = MagicMock()
    service.finish_schedule = MagicMock()
    data = FakeData({"ip": "127.0.0.1", "bk_cloud_id": 0})
    data.outputs.started_at = (timezone.now() - timedelta(hours=5)).isoformat()
    data.outputs.machine_started = 0
    data.outputs.max_wait_sec = DEFAULT_MAX_WAIT_SEC
    data.outputs.poll_rounds = 2

    assert service._schedule(data, None) is True
    assert data.outputs.timed_out == 1
    service.finish_schedule.assert_called_once()


def test_pre_flow_waits_before_triage():
    builder = MagicMock()
    info = {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_host_id": 1}
    with patch("backend.flow.engine.bamboo.scene.mongodb.mongodb_autofix_pre.Builder", return_value=builder,), patch(
        "backend.flow.plugins.components.collections.mongodb.mongo_autofix_pre_wait_machine._get_device_class",
        return_value="SA5.MEDIUM4",
    ):
        MongoAutofixPreFlow(root_id="root-1", data={"infos": [info]}).run()

    wait_acts = builder.add_parallel_acts.call_args.kwargs["acts_list"]
    assert wait_acts == [
        {
            "act_name": "等待机器启动-127.0.0.1-(标准类/4h/2m)",
            "act_component_code": MongoAutofixPreWaitMachineComponent.code,
            "kwargs": info,
        }
    ]
    triage_call = builder.add_act.call_args
    assert triage_call.kwargs["act_component_code"] == MongoAutofixPreTriageComponent.code
    assert triage_call.kwargs["kwargs"] == {"infos": [info]}
    builder.run_pipeline.assert_called_once()
