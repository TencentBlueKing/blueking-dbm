# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.db_meta.models import Cluster
from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
from backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise import RedisRollbackExerciseFlow
from backend.flow.engine.bamboo.scene.redis.revoke.redis_rollback_exercise_revoke_flow import (
    RedisRollbackExerciseRevokeFlow,
)
from backend.flow.engine.controller.redis import RedisController
from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
    RedisExerciseBestEffortCleanupComponent,
    RedisExerciseBestEffortCleanupService,
    RedisExerciseResourceApplyComponent,
    RedisExerciseResourceApplyService,
    RedisExerciseRevokeAppliedHostsComponent,
    RedisExerciseRevokeAppliedHostsService,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext


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

    def run_pipeline(self, **kwargs):
        self.run_kwargs = kwargs


@patch("backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise.Report.objects.get")
@patch("backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise.Cluster.objects.get")
def test_build_exercise_sub_flow_missing_cluster_marks_report_skipped(mock_cluster_get, mock_report_get):
    mock_cluster_get.side_effect = Cluster.DoesNotExist
    report = MagicMock()
    mock_report_get.return_value = report
    info = {
        "cluster_id": 123,
        "instance_ip": "1.1.1.1",
        "instance_port": 30000,
        "report_id": 456,
        "redis": [{"ip": "2.2.2.2"}],
    }
    ticket_data = {"infos": [info], "drill_config": {}, "bk_biz_id": 100, "created_by": "system"}
    flow = RedisRollbackExerciseFlow(root_id="root-id", data=ticket_data)

    result = flow._build_exercise_sub_flow(info, 0, ticket_data)

    assert result is None
    mock_report_get.assert_called_once_with(id=456)
    mock_cluster_get.assert_called_once_with(id=123)
    report.mark.assert_called_once()
    assert report.mark.call_args.args[0] == TaskStage.SKIPPED
    assert "123" in report.mark.call_args.kwargs["task_message"]


def test_redis_rollback_exercise_controller_exposes_revoke_flow():
    assert hasattr(RedisController.redis_rollback_exercise, "revoke_flow")
    assert RedisController.redis_rollback_exercise.revoke_flow == RedisRollbackExerciseRevokeFlow.revoke_flow


@patch("backend.flow.engine.bamboo.scene.redis.revoke.redis_rollback_exercise_revoke_flow.Builder", FakeBuilder)
def test_redis_rollback_revoke_flow_runs_best_effort_before_recycle_output():
    FakeBuilder.instances = []
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
    info = {
        "instance_ip": "1.1.1.4",
        "instance_port": 30000,
        "redis": [{"ip": "1.1.1.3"}],
    }
    RedisRollbackExerciseFlow._enrich_drill_prod_temp_instance_pairs(info)
    assert info["drill_prod_temp_instance_pairs"] == [["1.1.1.4:30000", "1.1.1.3:30000"]]


def test_revoke_applied_hosts_service_outputs_unique_redis_hosts():
    service = RedisExerciseRevokeAppliedHostsService()
    data = FakeData(
        {
            "global_data": {
                "job_root_id": "root-1",
                "infos": [
                    {
                        "redis": [
                            {
                                "ip": "1.1.1.1",
                                "bk_cloud_id": 0,
                                "bk_host_id": 101,
                            }
                        ]
                    },
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
    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowOutputHandler"
    ) as handler, patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.ResourceHandler"
    ) as resource_handler:
        resource_handler.standardized_resource_host.return_value = standardized_hosts
        service._execute_inner_captured(data, parent_data=None)

    resource_handler.standardized_resource_host.assert_called_once_with(
        [
            {
                "ip": "1.1.1.1",
                "bk_cloud_id": 0,
                "bk_host_id": 101,
                "remark": "Redis rollback exercise revoked",
            }
        ]
    )
    handler.return_value.insert_data.assert_called_once()
    root_id, hosts = handler.return_value.insert_data.call_args.args
    assert root_id == "root-1"
    assert hosts == [
        {
            "ip": "1.1.1.1",
            "bk_cloud_id": 0,
            "bk_host_id": 101,
            "remark": "Redis rollback exercise revoked",
            "city": "sz",
            "sub_zone": "sz-a",
            "rack_id": "rack-1",
            "os_name": "linux",
            "device_class": "S5",
        }
    ]


def test_revoke_applied_hosts_service_warns_when_cmdb_drops_hosts(caplog):
    caplog.set_level("WARNING")
    recycle_hosts = [
        {"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101, "remark": "keep"},
        {"ip": "2.2.2.2", "bk_cloud_id": 0, "bk_host_id": 102, "remark": "missing"},
    ]

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.ResourceHandler"
    ) as resource_handler:
        resource_handler.standardized_resource_host.return_value = [
            {"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101}
        ]

        hosts = RedisExerciseRevokeAppliedHostsService._standardize_recycle_hosts(recycle_hosts)

    assert hosts == [{"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101, "remark": "keep"}]
    assert "Recycle hosts dropped after CMDB normalization: [102]" in caplog.text


def test_revoke_applied_hosts_service_outputs_empty_table_when_no_redis_hosts():
    service = RedisExerciseRevokeAppliedHostsService()
    data = FakeData({"global_data": {"job_root_id": "root-1", "infos": [{"redis": []}, {}]}})

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowOutputHandler"
    ) as handler:
        service._execute_inner_captured(data, parent_data=None)

    handler.return_value.insert_data.assert_called_once_with("root-1", [])


@patch("backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise.Builder", FakeBuilder)
def test_rollback_exercise_flow_starts_with_resource_apply_act():
    FakeBuilder.instances = []
    info = {
        "cluster_id": 1,
        "instance_ip": "1.1.1.1",
        "instance_port": 30000,
        "report_id": 1,
        "redis": [{"ip": "2.2.2.2"}],
    }
    flow = RedisRollbackExerciseFlow(
        root_id="root-id",
        data={"infos": [info], "drill_config": {}, "bk_biz_id": 100, "created_by": "system"},
    )

    with patch.object(flow, "_build_exercise_sub_flow", return_value=None):
        flow.rollback_exercise_flow()

    builder = FakeBuilder.instances[0]
    assert builder.acts[0]["act_component_code"] == RedisExerciseResourceApplyComponent.code
    assert builder.acts[-1]["act_component_code"] == RedisExerciseBestEffortCleanupComponent.code


def test_resource_apply_service_logs_applied_host_summary():
    service = RedisExerciseResourceApplyService()
    infos = [
        {
            "cluster_id": 10,
            "cluster_domain": "cache.example.db",
            "instance_ip": "1.1.1.1",
            "instance_port": 30000,
            "redis": [
                {
                    "ip": "2.2.2.2",
                    "bk_host_id": 101,
                    "bk_cloud_id": 0,
                }
            ],
        }
    ]

    with patch.object(service, "log_info") as mock_log_info:
        service._log_applied_resources(infos, "req-123")

    assert mock_log_info.call_count == 1
    summary_log = mock_log_info.call_args_list[0].args[0]
    assert "演练资源申请完成，共 1 台主机 request_id=req-123" in summary_log
    assert "10:cache.example.db" in summary_log
    assert "    1.1.1.1:30000: 2.2.2.2" in summary_log


def test_resource_apply_service_log_summary_groups_instances_by_applied_ip():
    service = RedisExerciseResourceApplyService()
    infos = [
        {
            "cluster_id": 10,
            "cluster_domain": "cache.example.db",
            "instance_ip": "1.1.1.1",
            "instance_port": 30000,
            "redis": [{"ip": "2.2.2.2"}],
        },
        {
            "cluster_id": 10,
            "cluster_domain": "cache.example.db",
            "instance_ip": "1.1.1.1",
            "instance_port": 30001,
            "redis": [{"ip": "2.2.2.2"}],
        },
        {
            "cluster_id": 11,
            "cluster_domain": "cache.other.db",
            "instance_ip": "3.3.3.3",
            "instance_port": 30000,
            "redis": [{"ip": "4.4.4.4"}],
        },
    ]

    summary = service._build_resource_apply_log_summary(infos, header="applied")

    assert summary == "\n".join(
        [
            "applied",
            "10:cache.example.db",
            "    1.1.1.1:30000,1.1.1.1:30001: 2.2.2.2",
            "11:cache.other.db",
            "    3.3.3.3:30000: 4.4.4.4",
        ]
    )


def test_get_effective_drill_infos_prefers_trans_data_applied_infos():
    from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext
    from backend.flow.utils.redis.redis_rollback_exercise_resource import get_effective_drill_infos

    global_data = {"infos": [{"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000}]}
    trans_data = RedisRollbackExerciseContext(
        applied_infos=[
            {"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000, "redis": [{"ip": "2.2.2.2"}]}
        ]
    )

    infos = get_effective_drill_infos(global_data, trans_data)

    assert infos[0]["redis"][0]["ip"] == "2.2.2.2"


@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Report.objects.get")
def test_report_update_skips_rollback_started_without_applied_resource(mock_report_get):
    from backend.db_report.enums import RedisRollbackExerciseTaskStage as TaskStage
    from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
        RedisExerciseReportUpdateService,
    )
    from backend.flow.utils.redis.redis_context_dataclass import RedisRollbackExerciseContext

    service = RedisExerciseReportUpdateService()
    service.trans_data = RedisRollbackExerciseContext(
        applied_infos=[{"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000, "report_id": 8}]
    )
    data = FakeData(
        inputs={
            "kwargs": {
                "report_id": 8,
                "info_index": 0,
                "stage": TaskStage.ROLLBACK_STARTED,
            },
            "global_data": {"infos": [{"cluster_id": 1, "instance_ip": "1.1.1.1", "instance_port": 30000}]},
            "trans_data": service.trans_data,
        }
    )

    assert service._execute_inner_captured(data, {}) is True
    mock_report_get.assert_not_called()


def test_flow_runner_reads_applied_infos_from_trans_data():
    from backend.flow.plugins.components.collections.redis.redis_rollback_exercise import (
        RedisExerciseFlowRunnerService,
    )
    from backend.flow.utils.redis.redis_rollback_exercise_resource import info_has_applied_redis

    service = RedisExerciseFlowRunnerService()
    data = FakeData(
        inputs={
            "global_data": {
                "infos": [{"cluster_id": 24, "instance_ip": "1.1.1.1", "instance_port": 30000}],
            },
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


@patch("backend.flow.engine.bamboo.scene.redis.redis_rollback_exercise.get_instance_machine")
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
        info={
            "instance_ip": "1.1.1.1",
            "instance_port": 30000,
            "recovery_time_point": "2026-06-15 00:00:00",
            "redis": [{"ip": "2.2.2.2", "bk_host_id": 1, "bk_cloud_id": 0}],
        },
        cluster=cluster,
    )

    redis_spec = flow_data["infos"][0]["resource_spec"]["redis"]
    assert redis_spec["id"] == 42
    assert redis_spec["count"] == 1


@patch("backend.flow.plugins.components.collections.redis.redis_rollback_exercise.Report")
def test_reconcile_report_sanitizes_captured_logs_with_emoji(mock_report_model):
    from backend.db_report.models import RedisRollbackExerciseReport as Report

    report = Report()
    report.task_message = ""
    report.task_stage = TaskStage.ROLLBACK_FAILED
    report.save = MagicMock()
    mock_report_model.objects.get.return_value = report

    service = RedisExerciseBestEffortCleanupService()
    service.trans_data = RedisRollbackExerciseContext()
    service.trans_data.task_msg = ["[2026-06-15 16:50:46] [INFO]: [node] 任务正在执行🤔"]

    service._reconcile_report(15)

    assert "🤔" not in report.task_message
    assert "任务正在执行" in report.task_message
    report.save.assert_called_once()
