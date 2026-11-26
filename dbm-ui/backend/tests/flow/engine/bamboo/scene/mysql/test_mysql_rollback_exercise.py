# -*- coding: utf-8 -*-
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from backend.db_meta.enums import ClusterType
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskPhase, TaskStatus
from backend.db_report.enums import ReportStateType
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.scene.mysql.mysql_rollback_exercise import (
    MySQLRollbackExerciseFlow,
    calc_exercise_binlog_rollback_time,
)
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.delay import DelayComponent
from backend.flow.plugins.components.collections.common.sa_idle_check import CheckMachineIdleComponent
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
from backend.flow.plugins.components.collections.mysql.mysql_os_init import (
    CleanDataBakDirComponent,
    CleanDbExporterComponent,
)
from backend.flow.signal.mysql_rollback_exercise_handler import mysql_rollback_exercise_callback_handler
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
        self.timeline = []
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
        self.timeline.append(("act", act))
        return act

    def add_sub_pipeline(self, sub_flow):
        self.subs.append(sub_flow)
        self.timeline.append(("sub", sub_flow))

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


def _build_flow(
    cluster_type=ClusterType.TenDBHA.value,
    ticket_data=None,
    download_sub="full-download",
    download_ids=("dl-batch-1",),
):
    RecordingBuilder.instances = []
    flow = MySQLRollbackExerciseFlow(root_id="root-exercise", data=ticket_data or _ticket_data())
    cluster = _cluster_mock(cluster_type)

    def fake_download_sub_flow(**kwargs):
        collector = kwargs.get("download_node_ids")
        if collector is not None:
            collector.extend(download_ids)
        return download_sub

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
        f"{SCENE_MOD}.mysql_restore_download_sub_flow", side_effect=fake_download_sub_flow
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


class MysqlRollbackExercisePipelineTest(TestCase):
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
        self.assertIn(CleanDbExporterComponent.code, parent_codes)
        self.assertIn("destroy", parent.subs)

    def _parent_codes(self, template_id):
        with patch(f"{SCENE_MOD}.env.SA_CHECK_TEMPLATE_ID", template_id):
            builders = _build_flow()
        return [item.act_component_code for item in builders[0].acts]

    def test_exporter_cleanup_precedes_idle_check_when_template_set(self):
        codes = self._parent_codes("1")
        delay_idx = codes.index(DelayComponent.code)
        exporter_idx = codes.index(CleanDbExporterComponent.code)
        idle_idx = codes.index(CheckMachineIdleComponent.code)
        bak_idx = codes.index(CleanDataBakDirComponent.code)
        self.assertLess(exporter_idx, delay_idx)
        self.assertLess(delay_idx, idle_idx)
        self.assertLess(idle_idx, bak_idx)

    def test_exporter_cleanup_precedes_bak_cleanup_when_idle_check_skipped(self):
        codes = self._parent_codes("")
        self.assertNotIn(CheckMachineIdleComponent.code, codes)
        delay_idx = codes.index(DelayComponent.code)
        exporter_idx = codes.index(CleanDbExporterComponent.code)
        bak_idx = codes.index(CleanDataBakDirComponent.code)
        self.assertLess(exporter_idx, delay_idx)
        self.assertLess(delay_idx, bak_idx)

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
        self.assertIn("ReportStateType.ABNORMAL", mcp_src)
        self.assertIn("TaskPhase.DONE", mcp_src)
        self.assertIn("BINLOG_PREPARE_FAILED", model_src)
        self.assertIn("exercise_failed_statuses", model_src)

    def test_tendbcluster_uses_storage_path_without_spider_binlog(self):
        builders = _build_flow(cluster_type=ClusterType.TenDBCluster.value)
        names = [item.act_name for item in _flatten_acts(builders)]
        joined = " ".join(str(name) for name in names)
        self.assertNotIn("spider", joined.lower())
        self.assertNotIn("dbctl", joined.lower())
        self.assertTrue(any("查询演练窗口binlog" in str(name) for name in names))

    def test_no_timing_acts_and_recover_time_flags(self):
        builders = _build_flow()
        parent = builders[0]
        acts = _flatten_acts(builders)

        deploy_act = next(
            act for act in parent.acts if getattr(act, "kwargs", {}).get("task_status") == TaskStatus.DEPLOY_SUCCESS
        )
        self.assertFalse(deploy_act.kwargs.get("update_recover_time", True))
        self.assertFalse(any(act.kwargs.get("timing_stage") for act in acts))

        dl_sub_idx = next(
            idx for idx, (kind, item) in enumerate(parent.timeline) if kind == "sub" and item == "full-download"
        )
        restore_idx = next(
            idx
            for idx, (kind, item) in enumerate(parent.timeline)
            if kind == "act"
            and item.kwargs.get("get_mysql_payload_func") == MysqlActPayload.get_rollback_data_restore_payload.__name__
        )
        self.assertLess(dl_sub_idx, restore_idx)

        forward_builder = next(item for item in builders if item.sub_name == "全备恢复成功后前滚binlog")
        self.assertEqual(forward_builder.acts[0].act_component_code, MysqlExerciseBinlogQueryComponent.code)
        self.assertTrue(any(act.act_component_code == MysqlExerciseBinlogDownloadComponent.code for act in acts))

        apply_builder = next(item for item in builders if item.sub_name == "binlog apply")
        apply_ok = next(
            branch["act_object"] for branch in apply_builder.gateways[0]["branches"] if branch["express"] == "==0"
        )
        self.assertEqual(apply_ok.kwargs.get("task_status"), TaskStatus.RECOVER_SUCCESS)
        self.assertFalse(apply_ok.kwargs.get("update_recover_time", True))


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


class MysqlBackupRecoverTaskMetaTimingTest(TestCase):
    def _create_task(self, task_id: str, base_time):
        return MySQLBackupRecoverTask.objects.create(
            bk_biz_id=20,
            cluster_id=10,
            cluster_domain="timing.testha.db",
            cluster_type=ClusterType.TenDBHA.value,
            backup_id="b-timing",
            backup_begin_time=base_time - timedelta(hours=1),
            backup_end_time=base_time - timedelta(minutes=30),
            recover_start_time=base_time,
            recover_end_time=base_time,
            task_id=task_id,
            task_status=TaskStatus.COMMIT_SUCCESS,
            phase=TaskPhase.RUNNING,
            state="",
            creator="test_user",
            updater="test_user",
        )

    def _stamp(self, root_id, node_id, start, end):
        FlowNode.objects.create(root_id=root_id, node_id=node_id, version_id="")
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(started_at=start, updated_at=end)

    def _finish(self, root_id, node_id, states, outputs):
        engine = SimpleNamespace(
            get_node_state=lambda node: states[node],
            get_node_output_data=lambda node: SimpleNamespace(data=outputs.get(node, {})),
        )
        handler = "backend.flow.signal.mysql_rollback_exercise_handler"
        with patch(f"{handler}.BambooEngine", return_value=engine):
            mysql_rollback_exercise_callback_handler(root_id, node_id, StateType.FINISHED)

    def test_signal_writes_download_and_pure_recover(self):
        t0 = timezone.now() - timedelta(hours=1)
        dl_start = t0 + timedelta(minutes=5)
        dl_end = dl_start + timedelta(seconds=180)
        recover_start = dl_end + timedelta(seconds=30)
        recover_end = recover_start + timedelta(seconds=420)
        task = self._create_task("root-signal-ok", t0)
        task.exercise_timing_nodes = {
            "backup_download_node_ids": ["dl-a", "dl-b"],
            "recover_node_id": "recover-1",
        }
        task.save(update_fields=["exercise_timing_nodes"])
        self._stamp(task.task_id, "dl-a", dl_start, dl_start + timedelta(seconds=100))
        self._stamp(task.task_id, "dl-b", dl_start + timedelta(seconds=100), dl_end)
        self._stamp(task.task_id, "recover-1", recover_start, recover_end)
        clean = SimpleNamespace(name="FINISHED", skip=False, error_ignored=False)
        states = {
            "dl-a": clean,
            "dl-b": SimpleNamespace(name="RUNNING", skip=False, error_ignored=False),
            "recover-1": clean,
        }
        outputs = {
            "recover-1": {"rollback_code": 0, "job_execute": True},
        }

        self._finish(task.task_id, "dl-a", states, outputs)
        task.refresh_from_db()
        self.assertIsNone(task.backup_download_duration)

        states["dl-b"] = clean
        self._finish(task.task_id, "dl-b", states, outputs)
        task.refresh_from_db()
        self.assertEqual(task.backup_download_start_time, dl_start)
        self.assertEqual(task.backup_download_duration, 180)
        self.assertEqual(task.recover_start_time, t0)
        self.assertIsNone(task.recover_duration)

        self._finish(task.task_id, "recover-1", states, outputs)
        task.refresh_from_db()
        self.assertEqual(task.recover_start_time, recover_start)
        self.assertEqual(task.recover_end_time, recover_end)
        self.assertEqual(task.recover_duration, 420)
        self.assertEqual(task.task_status, TaskStatus.COMMIT_SUCCESS)

        self._finish(task.task_id, "binlog-apply", states, outputs)
        task.refresh_from_db()
        self.assertEqual(task.recover_duration, 420)
        self.assertEqual(task.recover_end_time, recover_end)

    def test_failed_or_skipped_steps_leave_duration_empty_and_recover_is_independent(self):
        t0 = timezone.now() - timedelta(hours=1)
        task = self._create_task("root-signal-fail", t0)
        task.exercise_timing_nodes = {
            "backup_download_node_ids": ["dl-a", "dl-b"],
            "recover_node_id": "recover-1",
        }
        task.save(update_fields=["exercise_timing_nodes"])
        start = t0 + timedelta(minutes=1)
        end = start + timedelta(seconds=60)
        for node_id in ("dl-a", "dl-b", "recover-1"):
            self._stamp(task.task_id, node_id, start, end)
        skipped = SimpleNamespace(name=StateType.FINISHED, skip=True, error_ignored=False)
        ignored = SimpleNamespace(name=StateType.FINISHED, skip=False, error_ignored=True)
        clean = SimpleNamespace(name=StateType.FINISHED, skip=False, error_ignored=False)
        states = {"dl-a": clean, "dl-b": skipped, "recover-1": ignored}
        outputs = {
            "recover-1": {"rollback_code": 0, "job_execute": True},
        }
        self._finish(task.task_id, "dl-b", states, outputs)
        self._finish(task.task_id, "recover-1", states, outputs)
        task.refresh_from_db()
        self.assertIsNone(task.backup_download_duration)
        self.assertIsNone(task.recover_duration)
        self.assertEqual(task.recover_start_time, t0)

        states["recover-1"] = clean
        self._finish(task.task_id, "recover-1", states, outputs)
        task.refresh_from_db()
        self.assertIsNone(task.backup_download_duration)
        self.assertEqual(task.recover_start_time, start)
        self.assertEqual(task.recover_duration, 60)

    def test_missing_node_ids_and_clock_rollback_do_not_write(self):
        t0 = timezone.now() - timedelta(minutes=10)
        task = self._create_task("root-signal-empty", t0)
        clean = SimpleNamespace(name=StateType.FINISHED, skip=False, error_ignored=False)
        self._finish(task.task_id, "other", {"other": clean}, {})
        task.refresh_from_db()
        self.assertIsNone(task.backup_download_duration)

        task.exercise_timing_nodes = {
            "backup_download_node_ids": ["dl-a"],
            "recover_node_id": "",
        }
        task.save(update_fields=["exercise_timing_nodes"])
        self._stamp(task.task_id, "dl-a", t0, t0 - timedelta(seconds=45))
        self._finish(task.task_id, "dl-a", {"dl-a": clean}, {})
        task.refresh_from_db()
        self.assertIsNone(task.backup_download_duration)

    def test_build_saves_download_and_restore_ids(self):
        base = timezone.now()
        task = self._create_task("root-exercise", base)
        builders = _build_flow(download_ids=("dl-batch-1", "dl-batch-2"))
        task.refresh_from_db()
        saved = task.exercise_timing_nodes
        restore = next(
            act
            for act in _flatten_acts(builders)
            if act.kwargs.get("get_mysql_payload_func") == MysqlActPayload.get_rollback_data_restore_payload.__name__
        )
        self.assertEqual(saved["backup_download_node_ids"], ["dl-batch-1", "dl-batch-2"])
        self.assertEqual(saved["recover_node_id"], restore.id)
        self.assertNotIn("binlog_download_node_id", saved)

    def test_report_hours_stay_blank_when_recover_is_incomplete(self):
        from backend.db_report.views.revover_drill_report_view import BackupRecoverTaskSerializer

        t0 = timezone.now()
        task = self._create_task("root-report", t0)
        task.recover_end_time = t0 - timedelta(hours=1)
        serializer = BackupRecoverTaskSerializer()
        self.assertIsNone(serializer.get_recover_duration(task))
        self.assertIsNone(serializer.get_backup_download_duration(task))

        # 新流程恢复失败：起止时间均为建记录默认值且结束略晚于开始，也应留空而不是 0.0
        task.exercise_timing_nodes = {"backup_download_node_ids": ["dl-a"], "recover_node_id": "recover-1"}
        task.recover_end_time = t0 + timedelta(microseconds=10)
        self.assertIsNone(serializer.get_recover_duration(task))

        task.recover_duration = 420
        task.backup_download_duration = 1800
        self.assertEqual(serializer.get_recover_duration(task), round(420 / 3600, 2))
        self.assertEqual(serializer.get_backup_download_duration(task), 0.5)

    def test_binlog_failure_does_not_clear_recorded_durations(self):
        t0 = timezone.now() - timedelta(minutes=30)
        task = self._create_task("root-timing-binlog-fail", t0)
        task.backup_download_duration = 60
        task.recover_duration = 120
        task.save(update_fields=["backup_download_duration", "recover_duration"])
        service = MySQLBackupRecoverTaskMetaSvr()
        service._execute(
            FakeData(
                {
                    "kwargs": {
                        "task_id": task.task_id,
                        "task_status": TaskStatus.BINLOG_APPLY_FAILED,
                    },
                    "trans_data": SimpleNamespace(rollback_error_info={"error_logs": "apply failed"}),
                }
            ),
            {},
        )
        task.refresh_from_db()
        self.assertEqual(task.task_status, TaskStatus.BINLOG_APPLY_FAILED)
        self.assertEqual(task.state, ReportStateType.ABNORMAL.value)
        self.assertEqual(task.backup_download_duration, 60)
        self.assertEqual(task.recover_duration, 120)

    def test_legacy_kwargs_without_update_recover_time_remain_compatible(self):
        t0 = timezone.now() - timedelta(minutes=20)
        t_deploy = t0 + timedelta(minutes=1)
        t_success = t0 + timedelta(minutes=10)

        task = self._create_task("root-legacy-compat", t0)
        service = MySQLBackupRecoverTaskMetaSvr()
        meta_mod = "backend.flow.plugins.components.collections.mysql.mysql_backup_recovery_exercise"

        with patch(f"{meta_mod}.timezone.now", return_value=t_deploy):
            service._execute(
                FakeData({"kwargs": {"task_id": task.task_id, "task_status": TaskStatus.DEPLOY_SUCCESS}}),
                {},
            )
        with patch(f"{meta_mod}.timezone.now", return_value=t_success):
            service._execute(
                FakeData({"kwargs": {"task_id": task.task_id, "task_status": TaskStatus.RECOVER_SUCCESS}}),
                {},
            )
        task.refresh_from_db()
        self.assertEqual(task.recover_start_time, t_deploy)
        self.assertEqual(task.recover_end_time, t_success)
        self.assertEqual(task.task_status, TaskStatus.RECOVER_SUCCESS)
        self.assertEqual(task.state, ReportStateType.NORMAL.value)
