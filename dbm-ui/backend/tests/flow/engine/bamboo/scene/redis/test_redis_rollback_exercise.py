# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise import RedisRollbackExerciseFlow
from backend.flow.engine.bamboo.scene.redis.revoke.redis_rollback_exercise_revoke_flow import (
    RedisRollbackExerciseRevokeFlow,
)
from backend.flow.engine.controller.redis import RedisController
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisExerciseBestEffortCleanupComponent,
    RedisExerciseBestEffortCleanupService,
    RedisExerciseFlowRunnerComponent,
    RedisExerciseFlowRunnerService,
    RedisExerciseReportUpdateService,
    RedisExerciseResourceApplyComponent,
    RedisExerciseResourceApplyService,
    RedisExerciseRevokeAppliedHostsComponent,
    RedisExerciseRevokeAppliedHostsService,
    RedisRollbackExerciseAlarmShieldComponent,
    merge_task_message,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
from backend.flow.utils.redis.redis_rollback_exercise_resource import get_effective_drill_infos, info_has_applied_redis

SCENE_MOD = "backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise"
COMPONENT_MOD = "backend.flow.plugins.components.collections.redis.redis_rollback_exercise"


class FakeData:
    def __init__(self, inputs=None):
        self.inputs = SimpleNamespace(**(inputs or {}))

    def get_one_of_inputs(self, key):
        return getattr(self.inputs, key, None)


class FakeBuilder:
    instances = []

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data
        self.acts = []
        self.run_kwargs = None
        self.__class__.instances.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        self.acts.append(
            {
                "act_name": act_name,
                "act_component_code": act_component_code,
                "kwargs": kwargs,
                "extra": extra,
            }
        )

    def add_parallel_sub_pipeline(self, sub_flow_list):
        self.sub_flows = sub_flow_list

    def add_conditional_subs(self, source_act, conditions, name, conditions_param):
        pass

    def build_sub_process(self, sub_name=None):
        return sub_name

    def run_pipeline(self, **kwargs):
        self.run_kwargs = kwargs


@pytest.fixture(autouse=True)
def _reset_fake_builder():
    FakeBuilder.instances = []
    yield
    FakeBuilder.instances = []


def _info(**overrides):
    info = {
        "cluster_id": 123,
        "instance_ip": "1.1.1.1",
        "instance_port": 30000,
        "report_id": 456,
        "redis": [{"ip": "2.2.2.2"}],
    }
    info.update(overrides)
    return info


def _ticket_data(info=None, drill_config=None, **overrides):
    data = {
        "infos": [info or _info()],
        "drill_config": {} if drill_config is None else drill_config,
        "bk_biz_id": 100,
        "created_by": "system",
    }
    data.update(overrides)
    return data


def _cluster_mock():
    cluster = MagicMock()
    cluster.id = 123
    cluster.bk_biz_id = 100
    cluster.immute_domain = "cache.test.db"
    return cluster


def _mock_source_machine(cpu, mem, disk, device_cls):
    return SimpleNamespace(
        spec_config={"cpu": {"min": cpu}, "mem": {"min": mem}},
        storage_device={"/data": {"size": disk}},
        bk_svr_device_cls_name=device_cls,
    )


@patch(f"{SCENE_MOD}.Report.objects.get")
@patch(f"{SCENE_MOD}.Cluster.objects.get")
def test_build_exercise_sub_flow_missing_cluster_marks_report_skipped(mock_cluster_get, mock_report_get):
    mock_cluster_get.side_effect = Cluster.DoesNotExist
    report = MagicMock()
    mock_report_get.return_value = report
    info = _info()
    ticket_data = _ticket_data(info)
    flow = RedisRollbackExerciseFlow(root_id="root-id", data=ticket_data)

    result = flow._build_exercise_sub_flow(info, 0, ticket_data)

    assert result is None
    mock_report_get.assert_called_once_with(id=456)
    mock_cluster_get.assert_called_once_with(id=123)
    report.mark.assert_called_once()
    assert report.mark.call_args.args[0] == TaskStage.SKIPPED
    assert "123" in report.mark.call_args.kwargs["task_message"]


def _build_sub_flow_with_config(drill_config: dict):
    info = _info()
    ticket_data = _ticket_data(info, drill_config=drill_config)
    flow = RedisRollbackExerciseFlow(root_id="root-id", data=ticket_data)
    with patch(f"{SCENE_MOD}.Report.objects.get") as mock_report_get, patch(
        f"{SCENE_MOD}.Cluster.objects.get"
    ) as mock_cluster_get, patch(f"{SCENE_MOD}.SubBuilder", FakeBuilder):
        mock_report_get.return_value = MagicMock()
        mock_cluster_get.return_value = _cluster_mock()
        sub = flow._build_exercise_sub_flow(info, 0, ticket_data)
    assert sub is not None
    acts = []
    for builder in FakeBuilder.instances:
        acts.extend(builder.acts)
    return acts


@pytest.mark.parametrize(
    "drill_config, error_ignorable, preserve, pause_count, shield_duration, shield_name_contains",
    [
        pytest.param({}, False, True, 2, max(3600, 4320 * 60), "4320.0 mins", id="preserve"),
        pytest.param({"error_ignorable": True}, True, False, 0, 3600, None, id="ignorable"),
    ],
)
def test_build_runner_flow_kwargs(
    drill_config, error_ignorable, preserve, pause_count, shield_duration, shield_name_contains
):
    acts = _build_sub_flow_with_config(drill_config)

    runner_acts = [a for a in acts if a["act_component_code"] == RedisExerciseFlowRunnerComponent.code]
    assert len(runner_acts) == 2
    for act in runner_acts:
        assert act["extra"]["error_ignorable"] is error_ignorable
        assert act["extra"]["retryable"] is False
        assert act["kwargs"]["preserve_scene_on_failure"] is preserve

    pause_acts = [a for a in acts if a["act_component_code"] == PauseComponent.code]
    assert len(pause_acts) == pause_count

    shield_act = next(a for a in acts if a["act_component_code"] == RedisRollbackExerciseAlarmShieldComponent.code)
    assert shield_act["kwargs"]["duration_seconds"] == shield_duration
    if shield_name_contains:
        assert shield_name_contains in shield_act["act_name"]


def test_real_builder_smoke_preserve_flow_pipeline_is_valid(monkeypatch):
    """Build a preserve-mode tree with the real SubBuilder so gateways/parallel subs pass bamboo validation."""
    from backend.flow.engine.bamboo.scene.common import builder as common_builder
    from backend.tests.mock_data.components.engine_run_pipeline import EngineApiMock

    ticket_data = _ticket_data(ticket_type="REDIS_ROLLBACK_EXERCISE")
    monkeypatch.setattr(common_builder.FlowNode.objects, "create", lambda **kwargs: None)
    monkeypatch.setattr(common_builder.FlowTree.objects, "create", lambda **kwargs: None)
    monkeypatch.setattr(common_builder.api, "run_pipeline", EngineApiMock.run_pipeline)
    monkeypatch.setattr(f"{SCENE_MOD}.Cluster.objects.get", lambda **kwargs: _cluster_mock())
    monkeypatch.setattr(f"{SCENE_MOD}.Report.objects.get", lambda **kwargs: MagicMock())
    EngineApiMock.was_called = False
    EngineApiMock.last_result = None
    EngineApiMock.last_exception = None

    RedisRollbackExerciseFlow(root_id="root-id", data=ticket_data).rollback_exercise_flow()

    assert EngineApiMock.was_called is True
    assert EngineApiMock.last_result is not None
    assert EngineApiMock.last_result.result is True, EngineApiMock.last_result.message


def test_redis_rollback_exercise_controller_exposes_revoke_flow():
    assert hasattr(RedisController.redis_rollback_exercise, "revoke_flow")
    assert RedisController.redis_rollback_exercise.revoke_flow == RedisRollbackExerciseRevokeFlow.revoke_flow


@patch("backend.flow.engine.bamboo.scene.redis.revoke.redis_rollback_exercise_revoke_flow.Builder", FakeBuilder)
def test_redis_rollback_revoke_flow_runs_best_effort_before_recycle_output():
    flow = RedisRollbackExerciseRevokeFlow(
        root_id="revoke-root",
        ticket_data={"uid": 999, "parent_ticket": 123, "infos": [], "bk_biz_id": 100},
    )

    flow.revoke_flow()

    builder = FakeBuilder.instances[0]
    assert builder.root_id == "revoke-root"
    assert builder.data["uid"] == 999
    assert builder.data["parent_ticket"] == 123
    assert [act["act_component_code"] for act in builder.acts] == [
        RedisExerciseBestEffortCleanupComponent.code,
        RedisExerciseRevokeAppliedHostsComponent.code,
    ]
    assert builder.acts[0]["extra"]["error_ignorable"] is True
    assert isinstance(builder.run_kwargs["init_trans_data_class"], RedisRollbackExerciseContext)


def test_best_effort_cleanup_uses_parent_ticket_for_rollback_tasks():
    service = RedisExerciseBestEffortCleanupService()

    assert service._get_rollback_task_ticket_id({"uid": 999, "parent_ticket": 123}) == 123
    assert service._get_rollback_task_ticket_id({"uid": 999}) == 999


def test_enrich_drill_prod_temp_instance_pairs_sets_expected_mapping():
    info = _info(instance_ip="1.1.1.4", redis=[{"ip": "1.1.1.3"}])
    RedisRollbackExerciseFlow._enrich_drill_prod_temp_instance_pairs(info)
    assert info["drill_prod_temp_instance_pairs"] == [["1.1.1.4:30000", "1.1.1.3:30000"]]


def test_revoke_applied_hosts_service_outputs_unique_redis_hosts():
    service = RedisExerciseRevokeAppliedHostsService()
    data = FakeData(
        {
            "global_data": {
                "job_root_id": "root-1",
                "infos": [
                    {"redis": [{"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101}]},
                    {"redis": [{"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101}]},
                    {"redis": [{"ip": "2.2.2.2", "bk_cloud_id": 0}]},
                ],
            }
        }
    )
    standardized_hosts = [
        {
            "ip": "1.1.1.1",
            "bk_cloud_id": 0,
            "bk_host_id": 101,
            "city": "sz",
            "sub_zone": "sz-a",
            "rack_id": "rack-1",
            "os_name": "linux",
            "device_class": "S5",
        }
    ]
    with patch(f"{COMPONENT_MOD}.FlowOutputHandler") as handler, patch(
        f"{COMPONENT_MOD}.ResourceHandler"
    ) as resource_handler:
        resource_handler.standardized_resource_host.return_value = standardized_hosts
        service._execute_inner_captured(data, parent_data=None)

    resource_handler.standardized_resource_host.assert_called_once_with(
        [{"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101, "remark": "Redis rollback exercise revoked"}]
    )
    handler.return_value.insert_data.assert_called_once()
    root_id, hosts = handler.return_value.insert_data.call_args.args
    assert root_id == "root-1"
    assert hosts == [{**standardized_hosts[0], "remark": "Redis rollback exercise revoked"}]


def test_revoke_applied_hosts_service_warns_when_cmdb_drops_hosts(caplog):
    caplog.set_level("WARNING")
    recycle_hosts = [
        {"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101, "remark": "keep"},
        {"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 102, "remark": "missing"},
    ]

    with patch(f"{COMPONENT_MOD}.ResourceHandler") as resource_handler:
        resource_handler.standardized_resource_host.return_value = [
            {"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101}
        ]
        hosts = RedisExerciseRevokeAppliedHostsService._standardize_recycle_hosts(recycle_hosts)

    assert hosts == [{"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101, "remark": "keep"}]
    assert "Recycle hosts dropped after CMDB normalization: [102]" in caplog.text


def test_revoke_applied_hosts_service_outputs_empty_table_when_no_redis_hosts():
    service = RedisExerciseRevokeAppliedHostsService()
    data = FakeData({"global_data": {"job_root_id": "root-1", "infos": [{"redis": []}, {}]}})

    with patch(f"{COMPONENT_MOD}.FlowOutputHandler") as handler:
        service._execute_inner_captured(data, parent_data=None)

    handler.return_value.insert_data.assert_called_once_with("root-1", [])


@patch(f"{SCENE_MOD}.Builder", FakeBuilder)
def test_rollback_exercise_flow_starts_with_resource_apply_act():
    flow = RedisRollbackExerciseFlow(
        root_id="root-id",
        data=_ticket_data(_info(cluster_id=1, report_id=1)),
    )

    with patch.object(flow, "_build_exercise_sub_flow", return_value=None):
        flow.rollback_exercise_flow()

    builder = FakeBuilder.instances[0]
    assert builder.acts[0]["act_component_code"] == RedisExerciseResourceApplyComponent.code
    assert builder.acts[-1]["act_component_code"] == RedisExerciseBestEffortCleanupComponent.code


def test_merge_task_message_deduplicates_prefix_snapshot():
    early = "\n".join(
        [
            "[2026-06-17 13:00:18] [INFO]: resource apply summary",
            "21000560:cache.example.db",
            "    1.1.1.1:30000: 2.2.2.2",
            "[2026-06-17 13:00:18] [INFO]: [apply act] success",
        ]
    )
    full = early + "\n[2026-06-17 13:06:47] [INFO]: cleanup finished"

    assert merge_task_message(early, full) == full
    assert merge_task_message(full, early) == full


def test_resource_apply_service_logs_applied_resources_only_once():
    service = RedisExerciseResourceApplyService()
    service.trans_data = RedisRollbackExerciseContext(resource_apply_logged=True)

    with patch.object(service, "log_info") as mock_log_info:
        service._log_applied_resources([{"cluster_id": 10, "redis": [{"ip": "2.2.2.2"}]}], "req-123")

    mock_log_info.assert_not_called()


@patch(f"{COMPONENT_MOD}.get_instance_machine")
@patch(f"{COMPONENT_MOD}.Cluster.objects.filter")
def test_resource_apply_service_logs_applied_host_summary(mock_cluster_filter, mock_get_instance_machine):
    mock_cluster_filter.return_value = [SimpleNamespace(id=10, immute_domain="cache.example.db")]
    mock_get_instance_machine.return_value = _mock_source_machine(4, 32, 500, "S5.4XLARGE16")

    service = RedisExerciseResourceApplyService()
    infos = [
        {
            "cluster_id": 10,
            "cluster_domain": "cache.example.db",
            "instance_ip": "1.1.1.1",
            "instance_port": 30000,
            "resource_spec": {"redis": {"spec_name": "2c_16g_200g"}},
            "redis": [
                {
                    "ip": "2.2.2.2",
                    "bk_host_id": 101,
                    "bk_cloud_id": 0,
                    "bk_cpu": 2,
                    "bk_mem": 16384,
                    "bk_disk": 200,
                    "bk_svr_device_cls_name": "SA5.MEDIUM4",
                }
            ],
        }
    ]

    with patch.object(service, "log_info") as mock_log_info:
        service._log_applied_resources(infos, "req-123")

    mock_log_info.assert_called_once()
    summary_log = mock_log_info.call_args.args[0]
    assert summary_log.startswith("演练资源申请完成，共 1 台主机 request_id=req-123")
    assert "2.2.2.2 (2 cores 16GB RAM 200GB disk)" in summary_log
    assert "1.1.1.1:30000 4 cores 32GB RAM 500GB disk" in summary_log


def test_resource_apply_service_format_applied_host_spec_uses_storage_device_fallback():
    service = RedisExerciseResourceApplyService()
    redis_host = {
        "bk_cpu": 4,
        "bk_mem": 32768,
        "storage_device": {"/data": {"size": 500}},
        "bk_svr_device_cls_name": "S5.4XLARGE16",
    }

    assert service._format_applied_host_spec(redis_host) == "4 cores 32GB RAM 500GB disk S5.4XLARGE16"


@patch(f"{COMPONENT_MOD}.get_instance_machine")
@patch(f"{COMPONENT_MOD}.Cluster.objects.filter")
def test_resource_apply_service_log_summary_groups_instances_by_applied_ip(
    mock_cluster_filter, mock_get_instance_machine
):
    mock_cluster_filter.return_value = [
        SimpleNamespace(id=10, immute_domain="cache.example.db"),
        SimpleNamespace(id=11, immute_domain="cache.other.db"),
    ]
    mock_get_instance_machine.return_value = _mock_source_machine(4, 32, 500, "S5.4XLARGE16")

    service = RedisExerciseResourceApplyService()
    infos = [
        {
            "cluster_id": 10,
            "cluster_domain": "cache.example.db",
            "instance_ip": "1.1.1.1",
            "instance_port": 30000,
            "redis": [
                {"ip": "2.2.2.2", "bk_cpu": 2, "bk_mem": 8192, "bk_disk": 100, "bk_svr_device_cls_name": "S5.LARGE8"}
            ],
        },
        {
            "cluster_id": 10,
            "cluster_domain": "cache.example.db",
            "instance_ip": "1.1.1.1",
            "instance_port": 30001,
            "redis": [
                {"ip": "2.2.2.2", "bk_cpu": 2, "bk_mem": 8192, "bk_disk": 100, "bk_svr_device_cls_name": "S5.LARGE8"}
            ],
        },
        {
            "cluster_id": 11,
            "cluster_domain": "cache.other.db",
            "instance_ip": "3.3.3.3",
            "instance_port": 30000,
            "redis": [
                {
                    "ip": "4.4.4.4",
                    "bk_cpu": 4,
                    "bk_mem": 16384,
                    "bk_disk": 200,
                    "bk_svr_device_cls_name": "S5.4XLARGE16",
                }
            ],
        },
    ]

    assert service._build_resource_apply_log_summary(infos, header="applied") == "\n".join(
        [
            "applied",
            "cache.example.db",
            "    2.2.2.2 (2 cores 8GB RAM 100GB disk)",
            "        1.1.1.1:30000 4 cores 32GB RAM 500GB disk",
            "        1.1.1.1:30001 4 cores 32GB RAM 500GB disk",
            "cache.other.db",
            "    4.4.4.4 (4 cores 16GB RAM 200GB disk)",
            "        3.3.3.3:30000 4 cores 32GB RAM 500GB disk",
        ]
    )


@patch(f"{COMPONENT_MOD}.get_instance_machine")
@patch(f"{COMPONENT_MOD}.Cluster.objects.filter")
def test_resource_apply_service_log_summary_shows_no_resource_with_instance_spec(
    mock_cluster_filter, mock_get_instance_machine
):
    mock_cluster_filter.return_value = [SimpleNamespace(id=10, immute_domain="cache.example.db")]
    mock_get_instance_machine.return_value = _mock_source_machine(2, 3, 120, "S5.MEDIUM4")

    service = RedisExerciseResourceApplyService()
    infos = [
        {"cluster_id": 10, "cluster_domain": "cache.example.db", "instance_ip": "5.5.5.5", "instance_port": 30000}
    ]

    summary = service._build_resource_apply_log_summary(
        infos,
        header="failed",
        include_applied_ip=False,
        no_resource_label="(no resource)",
    )

    assert summary == "\n".join(
        [
            "failed",
            "cache.example.db",
            "    (no resource)",
            "        5.5.5.5:30000 (2 cores 3GB RAM 120GB disk)",
        ]
    )


def test_get_effective_drill_infos_prefers_trans_data_applied_infos():
    global_data = {"infos": [{"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000}]}
    trans_data = RedisRollbackExerciseContext(
        applied_infos=[
            {"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000, "redis": [{"ip": "2.2.2.2"}]}
        ]
    )

    infos = get_effective_drill_infos(global_data, trans_data)

    assert infos[0]["redis"][0]["ip"] == "2.2.2.2"


@patch(f"{COMPONENT_MOD}.Report.objects.get")
def test_report_update_skips_rollback_started_without_applied_resource(mock_report_get):
    service = RedisExerciseReportUpdateService()
    service.trans_data = RedisRollbackExerciseContext(
        applied_infos=[{"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000, "report_id": 8}]
    )
    data = FakeData(
        inputs={
            "kwargs": {"report_id": 8, "info_index": 0, "stage": TaskStage.ROLLBACK_STARTED},
            "global_data": {"infos": [{"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000}]},
            "trans_data": service.trans_data,
        }
    )

    assert service._execute_inner_captured(data, {}) is True
    mock_report_get.assert_not_called()


def test_flow_runner_reads_applied_infos_from_trans_data():
    service = RedisExerciseFlowRunnerService()
    data = FakeData(
        inputs={
            "global_data": {"infos": [{"cluster_id": 24, "instance_ip": "1.1.1.1", "instance_port": 30000}]},
            "trans_data": RedisRollbackExerciseContext(
                applied_infos=[
                    {
                        "cluster_id": 24,
                        "instance_ip": "1.1.1.1",
                        "instance_port": 30000,
                        "redis": [{"ip": "2.2.2.2"}],
                    }
                ]
            ),
        }
    )

    info = service._get_effective_info(data, 0)

    assert info_has_applied_redis(info)
    assert info["redis"][0]["ip"] == "2.2.2.2"


@patch(f"{SCENE_MOD}.get_instance_machine")
def test_build_ds_flow_data_fills_resource_spec_from_source_machine(mock_get_machine):
    machine = MagicMock()
    machine.spec_id = 42
    machine.spec_config = {"cpu": {"min": 4, "max": 8}}
    mock_get_machine.return_value = machine

    cluster = MagicMock()
    cluster.id = 24
    cluster.bk_cloud_id = 0

    flow_data = RedisRollbackExerciseFlow.build_ds_flow_data(
        global_data={"bk_biz_id": 1, "uid": 99, "created_by": "system"},
        info=_info(
            recovery_time_point="2026-06-15 00:00:00",
            redis=[{"ip": "2.2.2.2", "bk_host_id": 1, "bk_cloud_id": 0}],
        ),
        cluster=cluster,
    )

    redis_spec = flow_data["infos"][0]["resource_spec"]["redis"]
    assert redis_spec["id"] == 42
    assert redis_spec["count"] == 1


def _cleanup_service_with_task_msg(messages):
    service = RedisExerciseBestEffortCleanupService()
    service.trans_data = RedisRollbackExerciseContext()
    service.trans_data.task_msg = messages
    return service


@patch(f"{COMPONENT_MOD}.Report")
def test_reconcile_report_deduplicates_existing_snapshot(mock_report_model):
    from backend.db_report.models import RedisRollbackExerciseReport as Report

    report = Report()
    report.task_message = "\n".join(
        [
            "[2026-06-17 13:00:18] [INFO]: resource apply summary",
            "21000560:cache.example.db",
        ]
    )
    report.task_stage = TaskStage.DONE
    report.save = MagicMock()
    mock_report_model.objects.get.return_value = report

    _cleanup_service_with_task_msg(
        [
            "[2026-06-17 13:00:18] [INFO]: resource apply summary\n21000560:cache.example.db",
            "[2026-06-17 13:06:47] [INFO]: cleanup finished",
        ]
    )._reconcile_report(15)

    assert report.task_message.count("resource apply summary") == 1
    assert "cleanup finished" in report.task_message
    report.save.assert_called_once()


@patch(f"{COMPONENT_MOD}.Report")
def test_reconcile_report_sanitizes_captured_logs_with_emoji(mock_report_model):
    from backend.db_report.models import RedisRollbackExerciseReport as Report

    report = Report()
    report.task_message = ""
    report.task_stage = TaskStage.ROLLBACK_FAILED
    report.save = MagicMock()
    mock_report_model.objects.get.return_value = report

    _cleanup_service_with_task_msg(["[2026-06-15 16:50:46] [INFO]: [node] 任务正在执行🤔"])._reconcile_report(15)

    assert "🤔" not in report.task_message
    assert "任务正在执行" in report.task_message
    report.save.assert_called_once()
