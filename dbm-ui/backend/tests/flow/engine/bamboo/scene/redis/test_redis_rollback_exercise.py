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
    flow = RedisRollbackExerciseFlow(
        root_id="root-id",
        data={"infos": [info], "drill_config": {}, "bk_biz_id": 100, "created_by": "system"},
    )

    result = flow._build_exercise_sub_flow(info)

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
    assert builder.data["uid"] == 123
    assert [act["act_component_code"] for act in builder.acts] == [
        RedisExerciseBestEffortCleanupComponent.code,
        RedisExerciseRevokeAppliedHostsComponent.code,
    ]
    assert builder.acts[0]["extra"]["error_ignorable"] is True
    assert isinstance(builder.run_kwargs["init_trans_data_class"], RedisRollbackExerciseContext)


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
                                "city": "sz",
                            }
                        ]
                    },
                    {"redis": [{"ip": "1.1.1.1", "bk_cloud_id": 0, "bk_host_id": 101}]},
                    {"redis": [{"ip": "2.2.2.2", "bk_cloud_id": 0}]},
                ],
            }
        }
    )

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowOutputHandler"
    ) as handler:
        service._execute_inner_captured(data, parent_data=None)

    handler.return_value.insert_data.assert_called_once()
    root_id, hosts = handler.return_value.insert_data.call_args.args
    assert root_id == "root-1"
    assert hosts == [
        {
            "ip": "1.1.1.1",
            "bk_cloud_id": 0,
            "bk_host_id": 101,
            "remark": "Redis rollback exercise revoked",
        }
    ]


def test_revoke_applied_hosts_service_outputs_empty_table_when_no_redis_hosts():
    service = RedisExerciseRevokeAppliedHostsService()
    data = FakeData({"global_data": {"job_root_id": "root-1", "infos": [{"redis": []}, {}]}})

    with patch(
        "backend.flow.plugins.components.collections.redis.redis_rollback_exercise.FlowOutputHandler"
    ) as handler:
        service._execute_inner_captured(data, parent_data=None)

    handler.return_value.insert_data.assert_called_once_with("root-1", [])
