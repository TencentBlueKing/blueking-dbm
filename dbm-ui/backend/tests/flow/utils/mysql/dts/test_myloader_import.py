# -*- coding: utf-8 -*-
"""DTS myloader 导入：build_dts_task_request / resolve_logical_backup / 子流程拼装冒烟。"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.types import TargetConfig
from backend.flow.consts import MySQLBackupTypeEnum
from backend.flow.utils.mysql.dts.backup_helper import resolve_logical_backup
from backend.flow.utils.mysql.dts.constants import (
    DEFAULT_MYLOADER_PATH,
    DtsLifecycleMode,
    FullLoadEngine,
    MigrateTopology,
    MigrateType,
)
from backend.flow.utils.mysql.dts.migrate_helper import build_dts_task_request
from backend.flow.utils.mysql.dts.migrate_plan import (
    DtsMigratePlan,
    DtsTaskConfig,
    DtsTaskSpec,
    MyloaderSpec,
    SourceSpec,
    SyncScope,
    build_migrate_plan,
)


def _minimal_plan() -> DtsMigratePlan:
    return DtsMigratePlan(
        topology=MigrateTopology.ONE_TO_ONE.value,
        migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
        dts_cluster_id=1,
        dts_lifecycle=DtsLifecycleMode.USE_EXISTING.value,
        auto_deploy_dts=False,
        deploy_subflow_inp=None,
        cleanup_after_migrate=False,
        recycle_dts_hosts=True,
        dts_task_config=DtsTaskConfig(full_load_engine=FullLoadEngine.MYLOADER.value),
        task_specs=[],
        worker_count_required=1,
        bk_biz_id=100,
        bk_cloud_id=0,
    )


def _myloader_task_spec(**kwargs) -> DtsTaskSpec:
    cfg = DtsTaskConfig(
        task_mode=kwargs.get("task_mode", "all"),
        full_load_engine=FullLoadEngine.MYLOADER.value,
    )
    return DtsTaskSpec(
        task_name="migrate-myloader-1",
        target_cluster_id=2,
        sources=[
            SourceSpec(
                cluster_id=1,
                source_name="src-1",
                sync_scope=SyncScope(do_dbs=["db_a"]),
                myloader=MyloaderSpec(
                    myloader_dir="/data/dbbak/root1/dts_myloader/src-1",
                    myloader_path=DEFAULT_MYLOADER_PATH,
                    threads=8,
                    regex="db_a\\..*",
                ),
            )
        ],
        target_config=TargetConfig(
            host="127.0.0.1",
            port=3306,
            user="u",
            password="p",
            cluster_type="mysql",
        ),
        dts_task_config=cfg,
    )


class BuildDtsTaskRequestMyloaderTest(SimpleTestCase):
    def test_myloader_branch_fills_myloaders_and_task_mode(self):
        plan = _minimal_plan()
        task_spec = _myloader_task_spec(task_mode="all")
        req = build_dts_task_request(plan, task_spec, user="u", password="p")
        self.assertEqual(req.task.task_mode, "myloader&sync")
        self.assertIsNone(req.task.source_config.full_migrate_conf)
        self.assertIn("myloader-src-1", req.task.source_config.myloaders)
        conf = req.task.source_config.myloaders["myloader-src-1"]
        self.assertEqual(conf.myloader_dir, "/data/dbbak/root1/dts_myloader/src-1")
        self.assertEqual(conf.myloader_path, DEFAULT_MYLOADER_PATH)
        self.assertEqual(conf.myloader_threads, 8)
        self.assertEqual(req.task.source_config.source_conf[0].myloader_config_name, "myloader-src-1")

    def test_myloader_full_mode_maps_to_myloader(self):
        plan = _minimal_plan()
        task_spec = _myloader_task_spec(task_mode="full")
        req = build_dts_task_request(plan, task_spec, user="u", password="p")
        self.assertEqual(req.task.task_mode, "myloader")

    def test_parse_full_load_engine_and_myloader_from_plan(self):
        details = {
            "dts_resource": {"mode": "use_existing", "dts_cluster_id": 9},
            "migrate": {
                "topology": MigrateTopology.ONE_TO_ONE.value,
                "one_to_one": {
                    "task_name": "mysql-dts-1-1-2",
                    "source": {"cluster_id": 1, "source_name": "src-1", "sync_scope": {"do_dbs": ["db_a"]}},
                    "target": {"cluster_id": 2},
                },
            },
            "task": {
                "full_load": {
                    "engine": FullLoadEngine.MYLOADER.value,
                    "myloader": {"threads": 12, "dest_worker_ip": "127.0.0.2"},
                }
            },
        }
        plan = build_migrate_plan(details)
        self.assertEqual(plan.dts_task_config.full_load_engine, FullLoadEngine.MYLOADER.value)
        self.assertIsNotNone(plan.task_specs[0].sources[0].myloader)
        self.assertEqual(plan.task_specs[0].sources[0].myloader.threads, 12)
        self.assertEqual(plan.task_specs[0].sources[0].myloader.dest_worker_ip, "127.0.0.2")


class ResolveLogicalBackupTest(SimpleTestCase):
    @patch("backend.flow.utils.mysql.dts.backup_helper.MySQLBackupHandler")
    def test_reject_non_logical_backup(self, handler_cls):
        handler = MagicMock()
        handler.get_tendb_latest_backup_info.return_value = {
            "backup_id": "bk-1",
            "backup_type": MySQLBackupTypeEnum.PHYSICAL.value,
            "task_ids": ["t1"],
            "local_files": [],
            "backup_host": "127.0.0.3",
        }
        handler_cls.return_value = handler

        with self.assertRaises(ValueError) as ctx:
            resolve_logical_backup(
                cluster_id=1,
                source_name="src-1",
                root_id="root1",
                myloader=MyloaderSpec(dest_worker_ip="127.0.0.2"),
                dest_worker_ip="127.0.0.2",
            )
        self.assertIn("logical", str(ctx.exception))

    @patch("backend.flow.utils.mysql.dts.backup_helper.MySQLBackupHandler")
    def test_accept_logical_backup(self, handler_cls):
        handler = MagicMock()
        handler.get_tendb_latest_backup_info.return_value = {
            "backup_id": "bk-logical-1",
            "backup_type": MySQLBackupTypeEnum.LOGICAL.value,
            "task_ids": ["task-a", "task-b"],
            "local_files": [],
            "backup_host": "127.0.0.3",
            "index": {"file_name": "index.json"},
        }
        handler_cls.return_value = handler

        resolved = resolve_logical_backup(
            cluster_id=1,
            source_name="src-1",
            root_id="root1",
            myloader=MyloaderSpec(dest_worker_ip="127.0.0.2"),
            dest_worker_ip="127.0.0.2",
        )
        self.assertEqual(resolved.backup_id, "bk-logical-1")
        self.assertEqual(resolved.task_ids, ["task-a", "task-b"])
        self.assertEqual(resolved.dest_worker_ip, "127.0.0.2")
        self.assertIn("src-1", resolved.myloader_dir)


class MyloaderSubflowSmokeTest(SimpleTestCase):
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_myloader_import_subflow.install_dbbackup_v2_subflow")
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_myloader_import_subflow.mysql_restore_download_sub_flow"
    )
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_myloader_import_subflow.resolve_task_logical_backups")
    def test_subflow_assembles_without_error(self, mock_resolve, mock_download, mock_install_dbbackup):
        from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_myloader_import_subflow import (
            mysql_dts_myloader_import_subflow,
        )
        from backend.flow.plugins.components.collections.mysql.dts.migrate.create_task import (
            MysqlDtsCreateTaskComponent,
        )
        from backend.flow.plugins.components.collections.mysql.dts.migrate.resolve_logical_backup import (
            MysqlDtsResolveLogicalBackupComponent,
        )
        from backend.flow.plugins.components.collections.mysql.dts.migrate.start_task import MysqlDtsStartTaskComponent
        from backend.flow.utils.mysql.dts.backup_helper import ResolvedLogicalBackup

        mock_install_dbbackup.return_value = MagicMock(name="install-dbbackup-sub")
        mock_download.return_value = MagicMock(name="download-sub")
        mock_resolve.return_value = [
            ResolvedLogicalBackup(
                cluster_id=1,
                source_name="src-1",
                backup_id="bk-1",
                backup_type=MySQLBackupTypeEnum.LOGICAL.value,
                backup_source="remote",
                task_ids=["tid-1"],
                local_files=[],
                backup_host="127.0.0.3",
                myloader_dir="/data/dbbak/root1/dts_myloader/src-1",
                dest_worker_ip="127.0.0.2",
            )
        ]
        plan = _minimal_plan()
        task_spec = _myloader_task_spec()
        with patch.object(SubBuilder, "add_act") as add_act, patch.object(SubBuilder, "add_sub_pipeline") as add_sub:
            mysql_dts_myloader_import_subflow(
                root_id="root1",
                bk_biz_id=100,
                ticket_id=18801,
                master_addr="127.0.0.1:18301",
                task_spec=task_spec,
                migrate_plan=plan,
                include_create_start=True,
            )
            codes = [call.kwargs.get("act_component_code") for call in add_act.call_args_list]
            self.assertIn(MysqlDtsResolveLogicalBackupComponent.code, codes)
            self.assertIn(MysqlDtsCreateTaskComponent.code, codes)
            self.assertIn(MysqlDtsStartTaskComponent.code, codes)
            self.assertEqual(add_sub.call_count, 2)
            mock_download.assert_called_once()
            mock_install_dbbackup.assert_called_once()
            # pipeline Act kwargs 必须 JSON 可序列化（不能直接塞 DtsTaskSpec / DtsMigratePlan）
            from backend.flow.utils.mysql.dts.migrate_plan import contains_dataclass

            for call in add_act.call_args_list:
                act_kwargs = call.kwargs.get("kwargs") or {}
                self.assertFalse(contains_dataclass(act_kwargs))
                if "task_spec" in act_kwargs:
                    self.assertIsInstance(act_kwargs["task_spec"], dict)
                if "migrate_plan" in act_kwargs:
                    self.assertIsInstance(act_kwargs["migrate_plan"], dict)

    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_catchup_cutover_subflow"
    )
    @patch(
        "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow.mysql_dts_myloader_import_subflow"
    )
    def test_migrate_task_hooks_myloader_subflow(self, mock_myloader_subflow, mock_catchup_cutover):
        from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow import (
            mysql_dts_migrate_task_subflow,
        )

        fake_sub = MagicMock()
        fake_sub.build_sub_process.return_value = MagicMock(name="myloader-sub")
        mock_myloader_subflow.return_value = fake_sub
        fake_catchup = MagicMock()
        fake_catchup.build_sub_process.return_value = MagicMock(name="catchup-cutover-sub")
        mock_catchup_cutover.return_value = fake_catchup

        plan = _minimal_plan()
        task_spec = _myloader_task_spec()
        with patch.object(SubBuilder, "add_sub_pipeline") as add_sub, patch.object(SubBuilder, "add_act"):
            mysql_dts_migrate_task_subflow(
                root_id="root1",
                bk_biz_id=100,
                ticket_id=18801,
                master_addr="127.0.0.1:18301",
                task_spec=task_spec,
                migrate_plan=plan,
            )
            mock_myloader_subflow.assert_called_once()
            mock_catchup_cutover.assert_called_once()
            add_sub.assert_called()
