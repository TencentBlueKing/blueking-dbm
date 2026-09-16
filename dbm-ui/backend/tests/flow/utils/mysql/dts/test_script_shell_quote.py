# -*- coding: utf-8 -*-
"""DTS Job shell：deploy_path / 节点名须 quote，且路径限制在 /data/dts 下。"""
import shlex

from django.test import SimpleTestCase

from backend.flow.utils.mysql.dts.constants import (
    get_default_deploy_path,
    validate_dts_cluster_name,
    validate_dts_deploy_path,
)
from backend.flow.utils.mysql.dts.script_template import (
    render_clean_data_dir_script,
    render_start_master_script,
    render_stop_process_script,
)
from backend.ticket.builders.mysql.dts.mysql_dts_tickets import DtsDeploySerializer


class DtsDeployPathGuardTest(SimpleTestCase):
    def test_accepts_path_under_data_dts(self):
        self.assertEqual(validate_dts_deploy_path("/data/dts/dts-make-test"), "/data/dts/dts-make-test")

    def test_rejects_quote_breakout(self):
        with self.assertRaises(ValueError):
            validate_dts_deploy_path('/data/dts/x"; id')

    def test_rejects_parent_dir(self):
        with self.assertRaises(ValueError):
            validate_dts_deploy_path("/data/dts/foo/../../etc")

    def test_rejects_outside_base(self):
        with self.assertRaises(ValueError):
            validate_dts_deploy_path("/tmp/dts")

    def test_cluster_name_rejects_meta(self):
        with self.assertRaises(ValueError):
            validate_dts_cluster_name('foo"; rm -rf /')
        with self.assertRaises(ValueError):
            get_default_deploy_path("foo/bar")


class DtsJobShellQuoteTest(SimpleTestCase):
    def test_stop_script_quotes_injectable_path(self):
        evil = '/data/dts/x"; id; echo "'
        script = render_stop_process_script(evil)
        assign = [line for line in script.splitlines() if line.startswith("DEPLOY_PATH=")][0]
        self.assertEqual(assign, "DEPLOY_PATH=" + shlex.quote(evil))
        self.assertNotIn('pkill -f "/data/dts/x"', script)
        self.assertIn('pkill -f "${DEPLOY_PATH}/bin/dm-worker"', script)

    def test_clean_script_uses_quoted_assignment(self):
        script = render_clean_data_dir_script("/data/dts/safe")
        self.assertIn("DEPLOY_PATH=" + shlex.quote("/data/dts/safe"), script)
        self.assertIn('rm -rf -- "${DEPLOY_PATH}"', script)
        self.assertNotIn('rm -rf "/data/dts/safe"', script)

    def test_start_script_quotes_node_name_and_path(self):
        script = render_start_master_script(
            deploy_path="/data/dts/demo",
            pkg_name="mysql-dts-v0.0.1.tar.gz",
            config_file="dm-master-1.toml",
            dts_node_name="dm-master-1",
        )
        self.assertIn("DEPLOY_PATH=" + shlex.quote("/data/dts/demo"), script)
        self.assertIn("DTS_NODE_NAME=" + shlex.quote("dm-master-1"), script)
        self.assertIn('start_daemon "${BIN_DIR}/dm-master" "${CONF_DIR}/${CONFIG_FILE}"', script)

    def test_start_script_quotes_injectable_node_name(self):
        evil_name = 'dm-master-1"; id; echo "'
        script = render_start_master_script(
            deploy_path="/data/dts/demo",
            pkg_name="mysql-dts-v0.0.1.tar.gz",
            config_file="dm-master-1.toml",
            dts_node_name=evil_name,
        )
        assign = [line for line in script.splitlines() if line.startswith("DTS_NODE_NAME=")][0]
        self.assertEqual(assign, "DTS_NODE_NAME=" + shlex.quote(evil_name))
        self.assertNotIn('DTS_NODE_NAME=dm-master-1"; id', script)


class DtsDeploySerializerPathTest(SimpleTestCase):
    def _data(self, **overrides):
        data = {
            "cluster_name": "dts-test",
            "bk_cloud_id": 0,
            "master_hosts": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
            "worker_hosts": [{"ip": "127.0.0.3", "bk_cloud_id": 0}],
        }
        data.update(overrides)
        return data

    def test_ticket_rejects_unquoted_shell_path(self):
        slz = DtsDeploySerializer(data=self._data(deploy_path='/data/dts/x"; id'))
        self.assertFalse(slz.is_valid())
        self.assertIn("deploy_path", slz.errors)

    def test_ticket_accepts_data_dts_path(self):
        slz = DtsDeploySerializer(data=self._data(deploy_path="/data/dts/dts-make-test"))
        self.assertTrue(slz.is_valid(), slz.errors)
