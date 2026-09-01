# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from backend.components.mysqldtsapi.types import TargetConfig
from backend.flow.utils.mysql.dts.constants import (
    DTS_CHECKPOINT_FLUSH_INTERVAL_DEFAULT,
    DTS_COLLATION_COMPATIBLE_STRICT,
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
)

CLUSTER_NAME = "dts-ut-cluster"


def _plan() -> DtsMigratePlan:
    return DtsMigratePlan(
        topology=MigrateTopology.ONE_TO_ONE.value,
        migrate_type=MigrateType.MYSQL_TO_MYSQL.value,
        dts_cluster_id=1,
        dts_lifecycle=DtsLifecycleMode.USE_EXISTING.value,
        auto_deploy_dts=False,
        deploy_subflow_inp=None,
        cleanup_after_migrate=False,
        recycle_dts_hosts=False,
        dts_task_config=DtsTaskConfig(),
        task_specs=[],
        worker_count_required=1,
    )


def _spec(*, task_mode="all", incr_migrate=None, full_load_engine=FullLoadEngine.BUILTIN.value) -> DtsTaskSpec:
    cfg = DtsTaskConfig(
        task_mode=task_mode,
        full_load_engine=full_load_engine,
        incr_migrate={} if incr_migrate is None else incr_migrate,
    )
    spec = DtsTaskSpec(
        task_name="mysql-dts-1-1-2",
        target_cluster_id=2,
        sources=[SourceSpec(cluster_id=1, source_name="src-1", sync_scope=SyncScope(do_dbs=["db_a"]))],
        target_config=TargetConfig(host="127.0.0.1", port=3306, user="u", password="p", cluster_type="mysql"),
        dts_task_config=cfg,
    )
    if full_load_engine == FullLoadEngine.MYLOADER.value:
        spec.sources[0].myloader = MyloaderSpec(
            myloader_dir="/data/dbbak/x",
            myloader_path="/home/mysql/dbbackup/bin/myloader",
            threads=8,
        )
    return spec


class BuildDtsTaskRequestNewVersionDefaultsTest(SimpleTestCase):
    def test_empty_options_force_strict_and_checkpoint_5(self):
        req = build_dts_task_request(_plan(), _spec(), user="u", password="p", cluster_name=CLUSTER_NAME)
        self.assertEqual(req.task.collation_compatible, DTS_COLLATION_COMPATIBLE_STRICT)
        self.assertIsNotNone(req.task.source_config.incr_migrate_conf)
        self.assertEqual(
            req.task.source_config.incr_migrate_conf.checkpoint_flush_interval,
            DTS_CHECKPOINT_FLUSH_INTERVAL_DEFAULT,
        )

    def test_engine_options_cannot_override_platform_values(self):
        spec = _spec(
            incr_migrate={"repl_threads": 8, "checkpoint_flush_interval": 30, "collation_compatible": "loose"}
        )
        req = build_dts_task_request(_plan(), spec, user="u", password="p", cluster_name=CLUSTER_NAME)
        self.assertEqual(req.task.collation_compatible, DTS_COLLATION_COMPATIBLE_STRICT)
        self.assertEqual(req.task.source_config.incr_migrate_conf.repl_threads, 8)
        self.assertEqual(
            req.task.source_config.incr_migrate_conf.checkpoint_flush_interval,
            DTS_CHECKPOINT_FLUSH_INTERVAL_DEFAULT,
        )

    def test_full_mode_does_not_invent_incr_checkpoint(self):
        req = build_dts_task_request(
            _plan(), _spec(task_mode="full"), user="u", password="p", cluster_name=CLUSTER_NAME
        )
        self.assertEqual(req.task.collation_compatible, DTS_COLLATION_COMPATIBLE_STRICT)
        self.assertIsNone(req.task.source_config.incr_migrate_conf)

    def test_myloader_incremental_also_strict_and_checkpoint_5(self):
        req = build_dts_task_request(
            _plan(),
            _spec(full_load_engine=FullLoadEngine.MYLOADER.value),
            user="u",
            password="p",
        )
        self.assertEqual(req.task.collation_compatible, DTS_COLLATION_COMPATIBLE_STRICT)
        self.assertEqual(
            req.task.source_config.incr_migrate_conf.checkpoint_flush_interval,
            DTS_CHECKPOINT_FLUSH_INTERVAL_DEFAULT,
        )

    def test_myloader_full_skips_checkpoint(self):
        req = build_dts_task_request(
            _plan(),
            _spec(task_mode="full", full_load_engine=FullLoadEngine.MYLOADER.value),
            user="u",
            password="p",
        )
        self.assertEqual(req.task.collation_compatible, DTS_COLLATION_COMPATIBLE_STRICT)
        self.assertIsNone(req.task.source_config.incr_migrate_conf)
