# -*- coding: utf-8 -*-
from unittest.mock import patch

from django.test import TestCase

from backend.db_meta.enums import AccessLayer, ClusterType, MachineType
from backend.db_meta.models import BKCity, LogicalCity, Machine, MysqlDtsCluster
from backend.db_meta.models.mysql_dts import MysqlDtsClusterStatus
from backend.db_proxy.reverse_api.mysql.impl.monitor_items_config import monitor_items_config
from backend.db_proxy.reverse_api.mysql.impl.monitor_runtime_config import monitor_runtime_config
from backend.flow.utils.mysql.dts.constants import MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT
from backend.tests.mock_data import constant

TEST_BK_CLOUD_ID = 0
MASTER_IP = "127.0.0.2"
WORKER_IP = "127.0.0.3"
COLOCATED_IP = "127.0.0.4"

_PLAT_ITEMS = {
    "dts-heartbeat": {
        "enable": True,
        "name": "dts-heartbeat",
        "role": [],
        "machine_type": ["mysql_dts_master", "mysql_dts_worker"],
        "schedule": "@every 30s",
    },
    "dts-task-status": {
        "enable": True,
        "name": "dts-task-status",
        "role": [],
        "machine_type": ["mysql_dts_master"],
        "schedule": "@every 30s",
    },
}


class DtsMonitorReverseApiTest(TestCase):
    def setUp(self):
        logical, _ = LogicalCity.objects.get_or_create(id=1, defaults={"name": "南京"})
        self.bk_city, _ = BKCity.objects.get_or_create(
            bk_idc_city_id=1,
            defaults={"logical_city": logical, "bk_idc_city_name": "南京"},
        )

    def _create_machine(self, ip, host_id, machine_type, access_layer):
        return Machine.objects.create(
            ip=ip,
            bk_biz_id=constant.BK_BIZ_ID,
            machine_type=machine_type,
            bk_city=self.bk_city,
            access_layer=access_layer,
            bk_host_id=host_id,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            cluster_type=ClusterType.MySQLDTS.value,
        )

    def _create_split_cluster(self):
        self._create_machine(MASTER_IP, 200001, MachineType.MYSQL_DTS_MASTER.value, AccessLayer.PROXY.value)
        self._create_machine(WORKER_IP, 200002, MachineType.MYSQL_DTS_WORKER.value, AccessLayer.STORAGE.value)
        return MysqlDtsCluster.objects.create(
            name="dts-rev",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            status=MysqlDtsClusterStatus.RUNNING.value,
            master_nodes=[{"ip": MASTER_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_MASTER_PORT}],
            worker_nodes=[{"ip": WORKER_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
            master_addr=f"{MASTER_IP}:{MYSQL_DTS_MASTER_PORT}",
            deploy_path="/data/dts/dts-rev",
        )

    def test_runtime_bypass_without_instance(self):
        self._create_split_cluster()
        master_cfgs = monitor_runtime_config(TEST_BK_CLOUD_ID, MASTER_IP, [MYSQL_DTS_MASTER_PORT])
        self.assertEqual(len(master_cfgs), 1)
        self.assertEqual(master_cfgs[0]["machine_type"], MachineType.MYSQL_DTS_MASTER.value)
        self.assertNotIn("dts_ticket_id", master_cfgs[0])
        self.assertEqual(master_cfgs[0]["auth"], {})
        self.assertEqual(master_cfgs[0]["bk_instance_id"], 0)
        self.assertNotIn("dts_master_addr", master_cfgs[0])
        self.assertNotIn("dts_metrics_addr", master_cfgs[0])
        self.assertNotIn("mysql", master_cfgs[0]["auth"])

        worker_cfgs = monitor_runtime_config(TEST_BK_CLOUD_ID, WORKER_IP, [MYSQL_DTS_WORKER_PORT])
        self.assertEqual(worker_cfgs[0]["machine_type"], MachineType.MYSQL_DTS_WORKER.value)

    @patch(
        "backend.db_proxy.reverse_api.mysql.impl.dts_monitor.DBConfigApi.query_conf_item",
        return_value={"content": _PLAT_ITEMS},
    )
    def test_items_from_plat_dbconfig(self, mock_query):
        self._create_split_cluster()
        items = monitor_items_config(TEST_BK_CLOUD_ID, MASTER_IP, [MYSQL_DTS_MASTER_PORT])
        self.assertEqual(set(items.keys()), {MYSQL_DTS_MASTER_PORT})
        self.assertIn("dts-heartbeat", items[MYSQL_DTS_MASTER_PORT])
        self.assertIn("dts-task-status", items[MYSQL_DTS_MASTER_PORT])
        self.assertNotIn("options", items[MYSQL_DTS_MASTER_PORT]["dts-task-status"])
        mock_query.assert_called_once()
        params = mock_query.call_args.args[0]
        self.assertEqual(params["namespace"], ClusterType.MySQLDTS.value)
        self.assertEqual(params["level_name"], "plat")
        self.assertEqual(params["level_value"], "0")
        self.assertEqual(params["bk_biz_id"], "0")

    def test_colocated_emits_two_role_runtimes(self):
        self._create_machine(COLOCATED_IP, 200003, MachineType.MYSQL_DTS_COLOCATED.value, AccessLayer.PROXY.value)
        MysqlDtsCluster.objects.create(
            name="dts-colo",
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=TEST_BK_CLOUD_ID,
            status=MysqlDtsClusterStatus.RUNNING.value,
            master_nodes=[{"ip": COLOCATED_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_MASTER_PORT}],
            worker_nodes=[{"ip": COLOCATED_IP, "bk_cloud_id": TEST_BK_CLOUD_ID, "port": MYSQL_DTS_WORKER_PORT}],
            master_addr=f"{COLOCATED_IP}:{MYSQL_DTS_MASTER_PORT}",
            deploy_path="/data/dts/dts-colo",
        )
        cfgs = monitor_runtime_config(TEST_BK_CLOUD_ID, COLOCATED_IP, [MYSQL_DTS_MASTER_PORT, MYSQL_DTS_WORKER_PORT])
        types = {c["machine_type"] for c in cfgs}
        self.assertEqual(types, {MachineType.MYSQL_DTS_MASTER.value, MachineType.MYSQL_DTS_WORKER.value})
        self.assertNotIn(MachineType.MYSQL_DTS_COLOCATED.value, types)
        self.assertTrue(all(c["auth"] == {} for c in cfgs))
        self.assertTrue(all("dts_ticket_id" not in c for c in cfgs))

    def test_runtime_empty_when_no_active_cluster(self):
        self._create_machine(MASTER_IP, 200001, MachineType.MYSQL_DTS_MASTER.value, AccessLayer.PROXY.value)
        self.assertEqual(monitor_runtime_config(TEST_BK_CLOUD_ID, MASTER_IP, [MYSQL_DTS_MASTER_PORT]), [])

    @patch(
        "backend.db_proxy.reverse_api.mysql.impl.dts_monitor.DBConfigApi.query_conf_item",
        return_value={"content": _PLAT_ITEMS},
    )
    def test_items_empty_when_no_active_cluster(self, mock_query):
        self._create_machine(WORKER_IP, 200002, MachineType.MYSQL_DTS_WORKER.value, AccessLayer.STORAGE.value)
        self.assertEqual(monitor_items_config(TEST_BK_CLOUD_ID, WORKER_IP, [MYSQL_DTS_WORKER_PORT]), {})
        mock_query.assert_not_called()

    @patch(
        "backend.flow.utils.mysql.act_payload.mysql.peripheraltools.list_nginx_addrs",
        return_value=["127.0.0.1:80"],
    )
    def test_gen_config_skips_spider_lookup_on_dts_proxy(self, _mock_nginx):
        from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import DeployPeripheralToolsDepart
        from backend.flow.utils.mysql.act_payload.mysql.peripheraltools import PeripheralToolsPayload

        self._create_machine(MASTER_IP, 200001, MachineType.MYSQL_DTS_MASTER.value, AccessLayer.PROXY.value)
        payload = PeripheralToolsPayload(
            bk_cloud_id=TEST_BK_CLOUD_ID,
            ticket_data={},
            cluster={
                "ports": [MYSQL_DTS_MASTER_PORT],
                "departs": [
                    DeployPeripheralToolsDepart.MySQLCrond,
                    DeployPeripheralToolsDepart.MySQLMonitor,
                ],
            },
        )
        result = payload.gen_config(ip=MASTER_IP)
        self.assertEqual(
            result["payload"]["extend"]["departs"],
            [DeployPeripheralToolsDepart.MySQLCrond, DeployPeripheralToolsDepart.MySQLMonitor],
        )
