# -*- coding: utf-8 -*-
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus
from backend.db_report.enums import ReportStateType
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise import (
    MySQLRollbackExerciseFlow,
    calc_exercise_binlog_rollback_time,
)
from backend.flow.plugins.components.collections.mysql.exec_switch_for_source_act import (
    ExecRollbackActForSourceComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_backup_recovery_exercise import (
    MySQLBackupRecoverTaskMetaSvr,
)
from backend.flow.plugins.components.collections.mysql.mysql_exercise_binlog_query import (
    MysqlExerciseBinlogDownloadComponent,
    MysqlExerciseBinlogQueryComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_os_init import CleanDataBakDirComponent
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.ticket.constants import TicketType
from backend.utils.time import str2datetime

SCENE_MOD = "backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise"


class FakeOutputs(SimpleNamespace):
    def __setitem__(self, key, value):
        setattr(self, key, value)


class FakeData:
    def __init__(self, inputs=None):
        self.inputs = inputs or {}
        self.outputs = FakeOutputs()

    def get_one_of_inputs(self, key):
        return self.inputs.get(key)


class RecordingBuilder:
    instances = []

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data
        self.acts = []
        self.subs = []
        self.gateways = []
        self.sub_name = None
        self.__class__.instances.append(self)

    def add_act(self, act_name, act_component_code, kwargs, **extra):
        act = SimpleNamespace(
            id=f"{id(self)}-{len(self.acts)}",
            act_name=act_name,
            act_component_code=act_component_code,
            kwargs=kwargs,
            extra=extra,
        )
        self.acts.append(act)
        return act

    def add_sub_pipeline(self, sub_flow):
        self.subs.append(sub_flow)

    def add_conditional_subs(self, source_act, conditions, name, conditions_param):
        self.gateways.append(
            {
                "source": source_act,
                "name": name,
                "param": conditions_param,
                "branches": [
                    {
                        "express": item.express,
                        "act_object": item.act_object,
                    }
                    for item in conditions
                ],
            }
        )

    def build_sub_process(self, sub_name=None):
        self.sub_name = sub_name
        return self


def _ticket_data(**overrides):
    data = {
        "ticket_type": TicketType.MYSQL_ROLLBACK_EXERCISE.value,
        "exercise_cluster_id": 1,
        "uid": "uid-1",
        "created_by": "system",
        "bk_biz_id": 20,
        "labels": [],
        "rollback_host": {"ip": "127.0.0.2", "bk_host_id": 23, "bk_cloud_id": 0},
        "backup_record": {
            "task_ids": ["full-1"],
            "backup_id": "b1",
            "backup_time": "2026-09-15T10:00:00+08:00",
            "backup_consistent_time": "2026-09-15T10:00:00+08:00",
            "backup_end_time": "2026-09-15T10:05:00+08:00",
            "binlog_info": {},
        },
        "pause_after_restore": False,
    }
    data.update(overrides)
    return data


def _cluster_mock(cluster_type=ClusterType.TenDBHA.value):
    cluster = MagicMock()
    cluster.id = 1
    cluster.bk_cloud_id = 0
    cluster.db_module_id = 1
    cluster.time_zone = "+08:00"
    cluster.region = "sz"
    cluster.name = "testha"
    cluster.immute_domain = "testha.db"
    cluster.major_version = "MySQL-5.7"
    cluster.bk_biz_id = 20
    cluster.cluster_type = cluster_type
    master = MagicMock()
    master.port = 20000
    cluster.storageinstance_set.filter.return_value.first.return_value = master
    shard0 = MagicMock()
    shard0.storage_instance_tuple.ejector = master
    cluster.tendbclusterstorageset_set.filter.return_value.first.return_value = shard0
    return cluster


def _build_flow(cluster_type=ClusterType.TenDBHA.value, ticket_data=None):
    RecordingBuilder.instances = []
    flow = MySQLRollbackExerciseFlow(root_id="root-exercise", data=ticket_data or _ticket_data())
    cluster = _cluster_mock(cluster_type)
    with patch(f"{SCENE_MOD}.SubBuilder", RecordingBuilder), patch(
        f"{SCENE_MOD}.Cluster.objects.get", return_value=cluster
    ), patch(f"{SCENE_MOD}.Package.get_latest_package", return_value=SimpleNamespace(name="mysql-5.7")), patch(
        f"{SCENE_MOD}.get_version_and_charset", return_value=("utf8", "MySQL-5.7")
    ), patch(
        f"{SCENE_MOD}.get_cluster_config", return_value={}
    ), patch(
        f"{SCENE_MOD}.generate_valid_domain", return_value="rb.testha.db"
    ), patch(
        f"{SCENE_MOD}.MySQLSingleApplyFlow"
    ) as mock_apply, patch(
        f"{SCENE_MOD}.mysql_restore_download_sub_flow", return_value="full-download"
    ), patch.object(
        MySQLRollbackExerciseFlow, "_build_reinstall_v2_dbbackup_subflow", return_value="reinstall"
    ), patch(
        f"{SCENE_MOD}.MySQLSingleDestroyFlow"
    ) as mock_destroy, patch(
        f"{SCENE_MOD}.get_resource_biz", return_value=20
    ), patch(
        f"{SCENE_MOD}.get_or_create_resource_module", return_value=1
    ):
        mock_apply.return_value.deploy_mysql_single_flow.return_value = "deploy"
        mock_destroy.return_value.destroy_mysql_single_subflow.return_value = "destroy"
        flow.build_rollback_exercise_flow()
    return RecordingBuilder.instances


def _flatten_acts(builders):
    acts = []
    for builder in builders:
        acts.extend(builder.acts)
    return acts


def _status_of(act_object):
    if isinstance(act_object, RecordingBuilder):
        return None
    kwargs = getattr(act_object, "kwargs", {}) or {}
    return kwargs.get("task_status")


class MysqlRollbackExercisePipelineTest(SimpleTestCase):
    def test_calc_rollback_time_is_backup_end_plus_one_hour(self):
        backup_end = "2026-09-15T10:05:00+08:00"
        got = calc_exercise_binlog_rollback_time(backup_end)
        self.assertEqual(str2datetime(got) - str2datetime(backup_end), timedelta(hours=1))

    def test_success_path_query_download_apply_then_recover_success(self):
        builders = _build_flow()
        acts = _flatten_acts(builders)
        codes = [item.act_component_code for item in acts]
        self.assertIn(MysqlExerciseBinlogQueryComponent.code, codes)
        self.assertIn(MysqlExerciseBinlogDownloadComponent.code, codes)
        apply_acts = [
            item
            for item in acts
            if item.act_component_code == ExecRollbackActForSourceComponent.code
            and item.kwargs.get("get_mysql_payload_func") == MysqlActPayload.tendb_recover_binlog_payload.__name__
        ]
        self.assertEqual(len(apply_acts), 1)
        apply_builder = next(item for item in builders if item.sub_name == "binlog apply")
        apply_gateway = apply_builder.gateways[0]
        success_status = _status_of(
            next(branch["act_object"] for branch in apply_gateway["branches"] if branch["express"] == "==0")
        )
        fail_status = _status_of(
            next(branch["act_object"] for branch in apply_gateway["branches"] if branch["express"] == "==1")
        )
        self.assertEqual(success_status, TaskStatus.RECOVER_SUCCESS)
        self.assertEqual(fail_status, TaskStatus.BINLOG_APPLY_FAILED)
        query_idx = codes.index(MysqlExerciseBinlogQueryComponent.code)
        download_idx = codes.index(MysqlExerciseBinlogDownloadComponent.code)
        apply_idx = next(
            idx
            for idx, item in enumerate(acts)
            if item.kwargs.get("get_mysql_payload_func") == MysqlActPayload.tendb_recover_binlog_payload.__name__
        )
        success_idx = next(
            idx
            for idx, item in enumerate(acts)
            if getattr(item, "kwargs", {}).get("task_status") == TaskStatus.RECOVER_SUCCESS
        )
        self.assertLess(query_idx, download_idx)
        self.assertLess(download_idx, apply_idx)
        self.assertLess(apply_idx, success_idx)

    def test_restore_failed_branch_has_no_binlog_forward(self):
        builders = _build_flow()
        parent = builders[0]
        restore_gateway = next(item for item in parent.gateways if item["param"] == "rollback_code")
        fail_branch = next(branch for branch in restore_gateway["branches"] if branch["express"] == "==1")
        success_branch = next(branch for branch in restore_gateway["branches"] if branch["express"] == "==0")
        self.assertEqual(_status_of(fail_branch["act_object"]), TaskStatus.RECOVER_FAILED)
        self.assertIsInstance(success_branch["act_object"], RecordingBuilder)
        fail_act = fail_branch["act_object"]
        self.assertNotEqual(fail_act.act_component_code, MysqlExerciseBinlogQueryComponent.code)

    def test_query_failed_writes_binlog_prepare_failed_and_cleanup_remains(self):
        builders = _build_flow()
        query_builder = next(item for item in builders if item.sub_name == "全备恢复成功后前滚binlog")
        query_gateway = query_builder.gateways[0]
        self.assertEqual(query_gateway["param"], "binlog_query_code")
        fail_status = _status_of(
            next(branch["act_object"] for branch in query_gateway["branches"] if branch["express"] == "==1")
        )
        self.assertEqual(fail_status, TaskStatus.BINLOG_PREPARE_FAILED)
        self.assertNotEqual(fail_status, TaskStatus.RECOVER_FAILED)
        parent = builders[0]
        parent_codes = [item.act_component_code for item in parent.acts]
        self.assertIn(CleanDataBakDirComponent.code, parent_codes)
        self.assertIn("destroy", parent.subs)

    def test_apply_failed_writes_binlog_apply_failed_not_recover_failed(self):
        builders = _build_flow()
        apply_builder = next(item for item in builders if item.sub_name == "binlog apply")
        fail_status = _status_of(
            next(
                branch["act_object"] for branch in apply_builder.gateways[0]["branches"] if branch["express"] == "==1"
            )
        )
        success_status = _status_of(
            next(
                branch["act_object"] for branch in apply_builder.gateways[0]["branches"] if branch["express"] == "==0"
            )
        )
        self.assertEqual(fail_status, TaskStatus.BINLOG_APPLY_FAILED)
        self.assertNotEqual(fail_status, TaskStatus.RECOVER_FAILED)
        self.assertEqual(success_status, TaskStatus.RECOVER_SUCCESS)
        apply_act = next(act for act in apply_builder.acts if "前滚binlog" in str(act.act_name))
        self.assertNotIn("write_payload_var", apply_act.extra)
        parent = builders[0]
        self.assertIn(CleanDataBakDirComponent.code, [item.act_component_code for item in parent.acts])

    def test_download_failed_writes_binlog_prepare_failed(self):
        builders = _build_flow()
        download_builder = next(item for item in builders if item.sub_name == "下载并前滚binlog")
        fail_status = _status_of(
            next(
                branch["act_object"]
                for branch in download_builder.gateways[0]["branches"]
                if branch["express"] == "==1"
            )
        )
        self.assertEqual(fail_status, TaskStatus.BINLOG_PREPARE_FAILED)
        self.assertNotEqual(fail_status, TaskStatus.RECOVER_FAILED)

    def test_failed_read_paths_include_binlog_apply_failed(self):
        from pathlib import Path

        backend = Path(__file__).resolve().parents[6]
        check_src = (backend / "db_periodic_task/local_tasks/mysql_backup_rollback/check_failed_task.py").read_text()
        mcp_src = (backend / "dbm_aiagent/mcp_tools/common/views/taskflow_query.py").read_text()
        model_src = (backend / "db_periodic_task/models.py").read_text()
        self.assertIn(TaskStatus.BINLOG_PREPARE_FAILED, TaskStatus.exercise_failed_statuses())
        self.assertIn(TaskStatus.BINLOG_APPLY_FAILED, TaskStatus.exercise_failed_statuses())
        self.assertIn("exercise_failed_statuses", check_src)
        self.assertIn("BINLOG_PREPARE_FAILED", mcp_src)
        self.assertIn("BINLOG_APPLY_FAILED", mcp_src)
        self.assertIn("BINLOG_PREPARE_FAILED", model_src)
        self.assertIn("exercise_failed_statuses", model_src)

    def test_tendbcluster_uses_storage_path_without_spider_binlog(self):
        builders = _build_flow(cluster_type=ClusterType.TenDBCluster.value)
        names = [item.act_name for item in _flatten_acts(builders)]
        joined = " ".join(str(name) for name in names)
        self.assertNotIn("spider", joined.lower())
        self.assertNotIn("dbctl", joined.lower())
        self.assertTrue(any("查询演练窗口binlog" in str(name) for name in names))


class MysqlBackupRecoverTaskMetaStickyTest(TestCase):
    def test_binlog_apply_failed_is_not_overwritten_by_resource_return(self):
        task = MySQLBackupRecoverTask.objects.create(
            bk_biz_id=20,
            cluster_id=1,
            cluster_domain="testha.db",
            cluster_type=ClusterType.TenDBHA.value,
            backup_id="b1",
            backup_begin_time=timezone.now(),
            backup_end_time=timezone.now(),
            task_id="root-sticky",
            task_status=TaskStatus.BINLOG_APPLY_FAILED,
            phase=TaskPhase.RUNNING,
            state=ReportStateType.ABNORMAL.value,
            creator="test_user",
            updater="test_user",
        )
        service = MySQLBackupRecoverTaskMetaSvr()
        data = FakeData(
            {
                "kwargs": {
                    "task_id": "root-sticky",
                    "task_status": TaskStatus.RESOURCE_RETURN_SUCCESS,
                },
                "trans_data": SimpleNamespace(rollback_error_info={}),
            }
        )
        self.assertTrue(service._execute(data, {}))
        task.refresh_from_db()
        self.assertEqual(task.task_status, TaskStatus.BINLOG_APPLY_FAILED)
        self.assertEqual(task.state, ReportStateType.ABNORMAL.value)

    def test_binlog_prepare_failed_is_not_overwritten_by_resource_return(self):
        task = MySQLBackupRecoverTask.objects.create(
            bk_biz_id=20,
            cluster_id=2,
            cluster_domain="testha.db",
            cluster_type=ClusterType.TenDBHA.value,
            backup_id="b2",
            backup_begin_time=timezone.now(),
            backup_end_time=timezone.now(),
            task_id="root-sticky-prepare",
            task_status=TaskStatus.BINLOG_PREPARE_FAILED,
            phase=TaskPhase.RUNNING,
            state=ReportStateType.ABNORMAL.value,
            creator="test_user",
            updater="test_user",
        )
        service = MySQLBackupRecoverTaskMetaSvr()
        data = FakeData(
            {
                "kwargs": {
                    "task_id": "root-sticky-prepare",
                    "task_status": TaskStatus.RESOURCE_RETURN_SUCCESS,
                },
                "trans_data": SimpleNamespace(rollback_error_info={}),
            }
        )
        self.assertTrue(service._execute(data, {}))
        task.refresh_from_db()
        self.assertEqual(task.task_status, TaskStatus.BINLOG_PREPARE_FAILED)
        self.assertEqual(task.state, ReportStateType.ABNORMAL.value)
