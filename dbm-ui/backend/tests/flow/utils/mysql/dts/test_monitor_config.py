# -*- coding: utf-8 -*-
import json
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_meta.enums import ClusterType, MachineType
from backend.flow.utils.mysql.dts.monitor_config import (
    group_monitor_roles,
    render_crond_runtime_yaml,
    render_items_config_yaml,
    render_monitor_config_yaml,
)

_DBCONFIG_ROOT = Path(__file__).resolve().parents[5] / "components" / "dbconfig" / "migrations" / "mysqldts"


class DtsMonitorConfigRenderTest(SimpleTestCase):
    @patch("backend.flow.utils.mysql.dts.monitor_config.env")
    @patch("backend.flow.utils.mysql.dts.monitor_config.SystemSettings.get_setting_value")
    def test_render_crond_runtime_yaml(self, mock_setting, mock_env):
        mock_setting.return_value = {
            "event": {"data_id": 1001, "token": "evt-token"},
            "metric": {"data_id": 1002, "token": "met-token"},
        }
        mock_env.MYSQL_CROND_BEAT_PATH = "/usr/local/gse/plugins/bin/bkmonitorbeat"
        mock_env.MYSQL_CROND_AGENT_ADDRESS = "/usr/local/gse/agent/data/ipc.state.report"

        text = render_crond_runtime_yaml(ip="127.0.0.2", bk_cloud_id=0)
        self.assertIn("127.0.0.2", text)
        self.assertIn("custom_metrics", text)
        self.assertIn("1002", text)
        self.assertIn("met-token", text)
        self.assertIn("/usr/local/gse/plugins/bin/bkmonitorbeat", text)

    def test_render_monitor_config_yaml_worker(self):
        text = render_monitor_config_yaml(
            bk_biz_id=20,
            ip="127.0.0.2",
            port=18501,
            machine_type=MachineType.MYSQL_DTS_WORKER.value,
            cluster_name="dts-mon",
            bk_cloud_id=0,
        )
        self.assertNotIn("dts_ticket_id", text)
        self.assertNotIn("dts_master_addr", text)
        self.assertNotIn("dts_metrics_addr", text)
        self.assertIn("machine_type: mysql_dts_worker", text)
        self.assertIn("18501", text)
        self.assertIn(f"cluster_type: {ClusterType.MySQLDTS.value}", text)
        self.assertIn("bk_instance_id: 0", text)
        self.assertNotIn("auth:\n  mysql:", text)

    def test_render_items_config_yaml(self):
        master_items = render_items_config_yaml(MachineType.MYSQL_DTS_MASTER.value)
        worker_items = render_items_config_yaml(MachineType.MYSQL_DTS_WORKER.value)
        self.assertIn("dts-heartbeat", master_items)
        self.assertIn("dts-task-status", master_items)
        self.assertNotIn("dts_master_addr", master_items)
        self.assertIn("dts-heartbeat", worker_items)
        self.assertNotIn("dts-task-status", worker_items)

    def test_group_monitor_roles_colocated(self):
        by_ip = group_monitor_roles(
            [{"ip": "127.0.0.2", "port": 18301, "bk_cloud_id": 0}],
            [{"ip": "127.0.0.2", "port": 18501, "bk_cloud_id": 0}],
        )
        self.assertEqual(list(by_ip.keys()), ["127.0.0.2"])
        ports = {r["port"] for r in by_ip["127.0.0.2"]["roles"]}
        self.assertEqual(ports, {18301, 18501})

    def test_mysqldts_dbconfig_has_only_two_items(self):
        file_def = json.loads((_DBCONFIG_ROOT / "mysqldts.json").read_text(encoding="utf-8"))
        self.assertEqual(len(file_def), 1)
        self.assertEqual(file_def[0]["conf_type"], "mysql_monitor")
        self.assertEqual(file_def[0]["conf_file"], "items-config.yaml")
        items = json.loads((_DBCONFIG_ROOT / "mysql_monitor" / "items-config.yaml.json").read_text(encoding="utf-8"))
        names = [row["conf_name"] for row in items]
        self.assertEqual(names, ["dts-heartbeat", "dts-task-status"])
        self.assertNotIn("db-up", names)
        self.assertIn("mysql_dts_master", items[1]["value_default"])
        self.assertNotIn("mysql_dts_worker", items[1]["value_default"])
