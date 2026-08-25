# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.components.mysqldtsapi.client import MySQLDTSApi
from backend.components.mysqldtsapi.types import FullMigrateConfig, SourceConfig, TargetConfig, Task
from backend.flow.plugins.components.collections.mysql.dts.migrate.create_task import MysqlDtsCreateTaskService
from backend.flow.utils.mysql.dts.constants import (
    DtsLifecycleMode,
    FullLoadEngine,
    MigrateTopology,
    MigrateType,
    get_full_migrate_data_dir,
)
from backend.flow.utils.mysql.dts.migrate_helper import (
    build_dts_task_request,
    build_full_migrate_config,
    resolve_dts_cluster_id,
    resolve_dts_cluster_name,
)
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskConfig, DtsTaskSpec, SourceSpec, SyncScope

CLUSTER_NAME = "dts-ywaq-sz-svr"
TASK_NAME = "mysql-dts-2410626-1004160"
EXPECTED_DATA_DIR = "/data/dts/dts-ywaq-sz-svr/exported_data/mysql-dts-2410626-1004160"


def _plan(**kwargs) -> DtsMigratePlan:
    return DtsMigratePlan(
        topology=MigrateTopology.ONE_TO_ONE.value,
        migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
        dts_cluster_id=kwargs.get("dts_cluster_id", 1),
        dts_lifecycle=DtsLifecycleMode.USE_EXISTING.value,
        auto_deploy_dts=False,
        deploy_subflow_inp=None,
        cleanup_after_migrate=False,
        recycle_dts_hosts=False,
        dts_task_config=DtsTaskConfig(full_load_engine=kwargs.get("full_load_engine", FullLoadEngine.BUILTIN.value)),
        task_specs=[],
        worker_count_required=1,
    )


def _task_spec(
    *, full_migrate=None, full_load_engine=FullLoadEngine.BUILTIN.value, task_name=TASK_NAME
) -> DtsTaskSpec:
    return DtsTaskSpec(
        task_name=task_name,
        target_cluster_id=2,
        sources=[SourceSpec(cluster_id=1, source_name="src-1", sync_scope=SyncScope(do_dbs=["db_a"]))],
        target_config=TargetConfig(host="127.0.0.1", port=3306, user="u", password="p", cluster_type="mysql"),
        dts_task_config=DtsTaskConfig(
            full_load_engine=full_load_engine,
            full_migrate={} if full_migrate is None else full_migrate,
        ),
    )


class BuildFullMigrateConfigTest(SimpleTestCase):
    def test_empty_full_migrate_fills_data_dir_and_disk_quota(self):
        conf = build_full_migrate_config(CLUSTER_NAME, TASK_NAME, None)
        self.assertEqual(conf.data_dir, EXPECTED_DATA_DIR)
        self.assertEqual(conf.disk_quota, "0")
        self.assertEqual(get_full_migrate_data_dir(CLUSTER_NAME, TASK_NAME), EXPECTED_DATA_DIR)

    def test_user_data_dir_is_ignored(self):
        conf = build_full_migrate_config(
            CLUSTER_NAME,
            TASK_NAME,
            {"data_dir": "/data/dts/1004160-21077171/exported_data", "import_threads": 32},
        )
        self.assertEqual(conf.data_dir, EXPECTED_DATA_DIR)
        self.assertEqual(conf.disk_quota, "0")
        self.assertEqual(conf.import_threads, 32)

    def test_json_null_full_migrate_treated_as_empty(self):
        conf = build_full_migrate_config(CLUSTER_NAME, TASK_NAME, None)
        self.assertEqual(conf.export_threads, 4)
        self.assertEqual(conf.import_threads, 16)


class BuildDtsTaskRequestFullMigrateTest(SimpleTestCase):
    def test_omitted_full_migrate_still_emits_conf(self):
        spec = _task_spec(full_migrate={})
        req = build_dts_task_request(_plan(), spec, user="u", password="p", cluster_name=CLUSTER_NAME)
        conf = req.task.source_config.full_migrate_conf
        self.assertIsNotNone(conf)
        self.assertEqual(conf.data_dir, EXPECTED_DATA_DIR)
        self.assertEqual(conf.disk_quota, "0")

    def test_builtin_requires_cluster_name(self):
        spec = _task_spec()
        with self.assertRaises(ValueError):
            build_dts_task_request(_plan(), spec, user="u", password="p")

    def test_myloader_skips_full_migrate_without_cluster_name(self):
        from backend.flow.utils.mysql.dts.migrate_plan import MyloaderSpec

        spec = _task_spec(full_load_engine=FullLoadEngine.MYLOADER.value)
        spec.sources[0].myloader = MyloaderSpec(
            myloader_dir="/data/dbbak/x",
            myloader_path="/home/mysql/dbbackup/bin/myloader",
            threads=8,
        )
        req = build_dts_task_request(_plan(), spec, user="u", password="p")
        self.assertIsNone(req.task.source_config.full_migrate_conf)


class DumpFullMigrateEmptyStrTest(SimpleTestCase):
    def _task(self, full_migrate: FullMigrateConfig | None) -> Task:
        return Task(
            name=TASK_NAME,
            task_mode="all",
            target_config=TargetConfig(host="127.0.0.1", port=3306, user="u", password="p", cluster_type="mysql"),
            source_config=SourceConfig(full_migrate_conf=full_migrate),
        )

    def test_dump_keeps_disk_quota_zero_and_strips_empty_optionals(self):
        dumped = MySQLDTSApi._dump_task(self._task(build_full_migrate_config(CLUSTER_NAME, TASK_NAME, {})))
        fm = dumped["source_config"]["full_migrate_conf"]
        self.assertEqual(fm["disk_quota"], "0")
        self.assertNotIn("compress-kv-pairs", fm)
        self.assertNotIn("pd_addr", fm)
        self.assertEqual(fm["data_dir"], EXPECTED_DATA_DIR)

    def test_dump_keeps_non_empty_optional_fields(self):
        dumped = MySQLDTSApi._dump_task(
            self._task(build_full_migrate_config(CLUSTER_NAME, TASK_NAME, {"pd_addr": "127.0.0.1:2379"}))
        )
        fm = dumped["source_config"]["full_migrate_conf"]
        self.assertEqual(fm["pd_addr"], "127.0.0.1:2379")
        self.assertEqual(fm["disk_quota"], "0")

    def test_dump_myloader_has_no_full_migrate_conf(self):
        dumped = MySQLDTSApi._dump_task(self._task(None))
        self.assertNotIn("full_migrate_conf", dumped["source_config"])


class ResolveDtsClusterIdTest(SimpleTestCase):
    def test_plan_id_wins_over_context(self):
        self.assertEqual(
            resolve_dts_cluster_id(SimpleNamespace(dts_cluster_id=9), SimpleNamespace(dts_cluster_id=3)), 9
        )

    def test_falls_back_to_context(self):
        self.assertEqual(
            resolve_dts_cluster_id(SimpleNamespace(dts_cluster_id=None), SimpleNamespace(dts_cluster_id=3)), 3
        )

    def test_zero_and_missing_are_empty(self):
        self.assertIsNone(resolve_dts_cluster_id(SimpleNamespace(dts_cluster_id=0), SimpleNamespace()))


class ResolveDtsClusterNameTest(SimpleTestCase):
    def test_deploy_name_wins_without_id(self):
        plan = SimpleNamespace(
            dts_cluster_id=None,
            deploy_subflow_inp=SimpleNamespace(cluster_name="dts-migrate-18801"),
        )
        self.assertEqual(resolve_dts_cluster_name(plan, SimpleNamespace()), "dts-migrate-18801")

    def test_missing_name_and_id_is_empty(self):
        plan = SimpleNamespace(dts_cluster_id=None, deploy_subflow_inp=None)
        self.assertIsNone(resolve_dts_cluster_name(plan, SimpleNamespace()))


class CreateTaskClusterLookupTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsCreateTaskService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        return service

    def _run(
        self,
        *,
        full_load_engine,
        dts_cluster_id=None,
        context_cluster_id=None,
        cluster_name="dts-ut",
        kwargs_cluster_name=None,
    ):
        task_spec = _task_spec(full_load_engine=full_load_engine)
        if full_load_engine == FullLoadEngine.MYLOADER.value:
            from backend.flow.utils.mysql.dts.migrate_plan import MyloaderSpec

            task_spec.sources[0].myloader = MyloaderSpec(
                myloader_dir="/data/dbbak/x",
                myloader_path="/home/mysql/dbbackup/bin/myloader",
            )
        migrate_context = SimpleNamespace(
            master_addr="127.0.0.1:8261",
            bk_cloud_id=0,
            dts_user="dts_u",
            dts_password="pwd",
            dts_cluster_id=context_cluster_id,
            myloader_dirs={},
            myloader_path="",
            target_host="",
            target_port=0,
            target_cluster_type="",
        )
        trans_data = SimpleNamespace(migrate_context=migrate_context)
        kwargs = {
            "master_addr": "127.0.0.1:8261",
            "bk_cloud_id": 0,
            "task_spec": {"task_name": task_spec.task_name},
            "migrate_plan": {},
        }
        if kwargs_cluster_name is not None:
            kwargs["cluster_name"] = kwargs_cluster_name
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": kwargs,
            "trans_data": trans_data,
        }.get(key)
        data.outputs = MagicMock()
        resp = SimpleNamespace(task={"name": task_spec.task_name}, check_result={"ok": True})
        plan = _plan(dts_cluster_id=dts_cluster_id)
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.MySQLDTSApi"
        ) as mock_api, patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.build_dts_task_request"
        ) as mock_build, patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.dts_migrate_plan_from_dict",
            return_value=plan,
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.dts_task_spec_from_dict",
            return_value=task_spec,
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task._apply_myloader_context_to_task_spec",
        ), patch(
            "backend.flow.utils.mysql.dts.migrate_helper.load_dts_cluster_name",
            return_value=cluster_name,
        ):
            mock_build.return_value = SimpleNamespace(
                task=SimpleNamespace(target_config=SimpleNamespace(host="127.0.0.1", port=3306, cluster_type="mysql"))
            )
            mock_api.create_task.return_value = resp
            ok = self._make_service()._execute(data, parent_data=None)
            return ok, mock_api, mock_build

    def test_builtin_uses_kwargs_cluster_name(self):
        ok, mock_api, mock_build = self._run(
            full_load_engine=FullLoadEngine.BUILTIN.value,
            dts_cluster_id=None,
            context_cluster_id=7,
            kwargs_cluster_name="dts-from-kwargs",
        )
        self.assertTrue(ok)
        mock_api.create_task.assert_called_once()
        self.assertEqual(mock_build.call_args.kwargs["cluster_name"], "dts-from-kwargs")

    def test_builtin_ignores_context_cluster_id(self):
        ok, mock_api, unused_build = self._run(
            full_load_engine=FullLoadEngine.BUILTIN.value,
            dts_cluster_id=None,
            context_cluster_id=7,
        )
        self.assertFalse(ok)
        mock_api.create_task.assert_not_called()

    def test_builtin_uses_deploy_name_without_id(self):
        task_spec = _task_spec(full_load_engine=FullLoadEngine.BUILTIN.value)
        migrate_context = SimpleNamespace(
            master_addr="127.0.0.1:8261",
            bk_cloud_id=0,
            dts_user="dts_u",
            dts_password="pwd",
            dts_cluster_id=None,
            myloader_dirs={},
            myloader_path="",
            target_host="",
            target_port=0,
            target_cluster_type="",
        )
        trans_data = SimpleNamespace(migrate_context=migrate_context)
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "master_addr": "127.0.0.1:8261",
                "bk_cloud_id": 0,
                "task_spec": {"task_name": task_spec.task_name},
                "migrate_plan": {},
            },
            "trans_data": trans_data,
        }.get(key)
        data.outputs = MagicMock()
        plan = _plan(dts_cluster_id=None)
        plan.deploy_subflow_inp = SimpleNamespace(cluster_name="dts-migrate-18801")
        resp = SimpleNamespace(task={"name": task_spec.task_name}, check_result={"ok": True})
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.MySQLDTSApi"
        ) as mock_api, patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.build_dts_task_request"
        ) as mock_build, patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.dts_migrate_plan_from_dict",
            return_value=plan,
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task.dts_task_spec_from_dict",
            return_value=task_spec,
        ), patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.create_task._apply_myloader_context_to_task_spec",
        ), patch(
            "backend.flow.utils.mysql.dts.migrate_helper.load_dts_cluster_name",
        ) as mock_load:
            mock_build.return_value = SimpleNamespace(
                task=SimpleNamespace(target_config=SimpleNamespace(host="127.0.0.1", port=3306, cluster_type="mysql"))
            )
            mock_api.create_task.return_value = resp
            ok = self._make_service()._execute(data, parent_data=None)
        self.assertTrue(ok)
        mock_load.assert_not_called()
        self.assertEqual(mock_build.call_args.kwargs["cluster_name"], "dts-migrate-18801")

    def test_builtin_missing_cluster_id_fails_without_api(self):
        ok, mock_api, unused_build = self._run(
            full_load_engine=FullLoadEngine.BUILTIN.value,
            dts_cluster_id=None,
            context_cluster_id=None,
        )
        self.assertFalse(ok)
        mock_api.create_task.assert_not_called()

    def test_builtin_missing_cluster_name_fails_without_api(self):
        ok, mock_api, unused_build = self._run(
            full_load_engine=FullLoadEngine.BUILTIN.value,
            dts_cluster_id=1,
            cluster_name=None,
        )
        self.assertFalse(ok)
        mock_api.create_task.assert_not_called()

    def test_myloader_missing_cluster_id_still_creates(self):
        ok, mock_api, mock_build = self._run(
            full_load_engine=FullLoadEngine.MYLOADER.value,
            dts_cluster_id=None,
            context_cluster_id=None,
        )
        self.assertTrue(ok)
        mock_api.create_task.assert_called_once()
        self.assertIsNone(mock_build.call_args.kwargs["cluster_name"])
