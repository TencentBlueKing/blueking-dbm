# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.dts.migrate.poll_catchup import MysqlDtsPollCatchupComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket import MySQLCheckSumTicketComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket_result_get import (
    MySQLCheckSumTicketResultComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket_status import (
    MySQLCheckSumTicketProbeComponent,
)
from backend.flow.utils.mysql.dts.context import MysqlDtsChecksumSubflowInput
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskSpec, SourceSpec, SyncScope


class MysqlDtsChecksumSubflowWiringTest(SimpleTestCase):
    def _build_codes(self, *, need_catchup_before_result: bool):
        acts = []

        class FakeSub:
            def add_act(self, **kwargs):
                acts.append(kwargs)

            def build_sub_process(self, *a, **k):
                return self

        task_spec = DtsTaskSpec(
            task_name="t1",
            target_cluster_id=2,
            sources=[
                SourceSpec(
                    cluster_id=1,
                    source_name="s1",
                    sync_scope=SyncScope(do_dbs=["db"], do_tables=[{"schema": "*", "table": "*"}]),
                )
            ],
        )
        inp = MysqlDtsChecksumSubflowInput(
            root_id="r1",
            bk_biz_id=3,
            ticket_id=9,
            master_addr="127.0.0.2:8261",
            task_name="t1",
            bk_cloud_id=0,
            source_name_list=["s1"],
        )
        fake_info = {
            "details": {
                "infos": [
                    {
                        "cluster_id": 1,
                        "master": {"ip": "127.0.0.1", "port": 3306},
                        "slaves": [{"ip": "127.0.0.3", "port": 3306}],
                    }
                ]
            }
        }
        fake_cluster = MagicMock()
        fake_cluster.bk_cloud_id = 0
        with (
            patch(
                "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow.build_dts_checksum_ticket_info",
                return_value=fake_info,
            ),
            patch(
                "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow.Cluster.objects.get",
                return_value=fake_cluster,
            ),
            patch(
                "backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow.SubBuilder",
                return_value=FakeSub(),
            ),
        ):
            from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow import (
                mysql_dts_checksum_subflow,
            )

            mysql_dts_checksum_subflow(
                inp=inp,
                task_spec=task_spec,
                need_catchup_before_result=need_catchup_before_result,
            )
        return [a["act_component_code"] for a in acts]

    def test_catchup_inserted_between_probe_and_result_when_enabled(self):
        codes = self._build_codes(need_catchup_before_result=True)
        self.assertEqual(
            codes,
            [
                MySQLCheckSumTicketComponent.code,
                MySQLCheckSumTicketProbeComponent.code,
                MysqlDtsPollCatchupComponent.code,
                MySQLCheckSumTicketResultComponent.code,
            ],
        )

    def test_no_catchup_when_disabled(self):
        codes = self._build_codes(need_catchup_before_result=False)
        self.assertEqual(
            codes,
            [
                MySQLCheckSumTicketComponent.code,
                MySQLCheckSumTicketProbeComponent.code,
                MySQLCheckSumTicketResultComponent.code,
            ],
        )
