# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_reinstall_subflow import _collect_reinstall_hosts
from backend.flow.utils.mysql.dts.context import DtsHostSpec, MysqlDtsReinstallSubflowInput
from backend.flow.utils.mysql.dts.script_template import render_reinstall_master_script, render_reinstall_worker_script


class CollectReinstallHostsTest(SimpleTestCase):
    """测试重装主机收集（按 IP 去重）。"""

    def test_dedupes_colocated_hosts(self):
        inp = MysqlDtsReinstallSubflowInput(
            root_id="test",
            dts_cluster_id=1,
            bk_biz_id=1,
            bk_cloud_id=0,
            master_addr="127.0.0.2:18301",
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0, "name": "dm-master-1"}],
            worker_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0, "name": "dm-worker-1"}],
            deploy_path="/data/dts/test",
        )
        hosts = _collect_reinstall_hosts(inp)
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].ip, "127.0.0.2")

    def test_collects_distinct_hosts(self):
        inp = MysqlDtsReinstallSubflowInput(
            root_id="test",
            dts_cluster_id=1,
            bk_biz_id=1,
            bk_cloud_id=0,
            master_addr="127.0.0.2:18301",
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0, "name": "dm-master-1"}],
            worker_nodes=[
                {"ip": "127.0.0.3", "bk_cloud_id": 0, "name": "dm-worker-1"},
                {"ip": "127.0.0.4", "bk_cloud_id": 0, "name": "dm-worker-2"},
            ],
            deploy_path="/data/dts/test",
        )
        hosts = _collect_reinstall_hosts(inp)
        self.assertEqual(len(hosts), 3)
        ips = {h.ip for h in hosts}
        self.assertEqual(ips, {"127.0.0.2", "127.0.0.3", "127.0.0.4"})


class BuildDtsTransFileKwargsTest(SimpleTestCase):
    """介质下发 kwargs：解析 Package 并返回 pkg_name（不回写元数据 version）。"""

    @patch("backend.flow.utils.mysql.dts.package_resolver.build_mysql_dts_bkrepo_paths")
    @patch("backend.flow.utils.mysql.dts.package_resolver.resolve_mysql_dts_package")
    def test_returns_pkg_name_for_transfile(self, mock_resolve, mock_paths):
        from backend.flow.engine.bamboo.scene.mysql.dts.subflow_common import build_dts_trans_file_kwargs

        mock_resolve.return_value = SimpleNamespace(
            id=99,
            path="mysql/dts/mysql-dts-v2.0.1.tar.gz",
        )
        mock_paths.return_value = (["bk-dbm/mysql/dts/mysql-dts-v2.0.1.tar.gz"], "mysql-dts-v2.0.1.tar.gz")

        unused_kwargs, pkg_name = build_dts_trans_file_kwargs(
            [DtsHostSpec(ip="127.0.0.2", bk_cloud_id=0)],
            bk_cloud_id=0,
            dts_pkg_id=99,
        )
        self.assertEqual(pkg_name, "mysql-dts-v2.0.1.tar.gz")
        self.assertEqual(unused_kwargs["file_list"], ["bk-dbm/mysql/dts/mysql-dts-v2.0.1.tar.gz"])
        mock_resolve.assert_called_once_with(pkg_id=99)


class ReinstallScriptTemplateTest(SimpleTestCase):
    """测试重装脚本模板渲染。"""

    def test_master_script_contains_symlink(self):
        script = render_reinstall_master_script(
            deploy_path="/data/dts/test",
            pkg_name="mysql-dts-v2.0.1.tar.gz",
            config_file="dm-master-1.toml",
            dts_node_name="dm-master-1",
        )
        # 整目录软链 bin，而非逐个二进制；已是软链时只 rm -f 链接
        self.assertIn('ln -sfn "${PKG_BIN}" "${BIN_DIR}"', script)
        self.assertIn('if [[ -L "${BIN_DIR}" ]]; then', script)
        self.assertIn('rm -f "${BIN_DIR}"', script)
        self.assertIn('rm -rf "${BIN_DIR}"', script)
        self.assertIn("dm-master", script)
        self.assertIn("/data/dts/test/packages/", script)

    def test_master_script_does_not_push_config(self):
        script = render_reinstall_master_script(
            deploy_path="/data/dts/test",
            pkg_name="mysql-dts-v2.0.1.tar.gz",
            config_file="dm-master-1.toml",
            dts_node_name="dm-master-1",
        )
        self.assertNotIn("cat >", script)
        self.assertNotIn("DTS_CONFIG_EOF", script)

    def test_worker_script_contains_symlink(self):
        script = render_reinstall_worker_script(
            deploy_path="/data/dts/test",
            pkg_name="mysql-dts-v2.0.1.tar.gz",
            config_file="dm-worker-1.toml",
            dts_node_name="dm-worker-1",
        )
        self.assertIn('ln -sfn "${PKG_BIN}" "${BIN_DIR}"', script)
        self.assertIn('if [[ -L "${BIN_DIR}" ]]; then', script)
        self.assertIn("dm-worker", script)
        self.assertIn("/data/dts/test/packages/", script)

    def test_script_extracts_to_isolation_dir(self):
        script = render_reinstall_master_script(
            deploy_path="/data/dts/test",
            pkg_name="mysql-dts-v2.0.1.tar.gz",
            config_file="dm-master-1.toml",
            dts_node_name="dm-master-1",
        )
        self.assertIn('PKG_ROOT="${DEPLOY_PATH}/packages/${PKG_BASENAME}"', script)
        self.assertIn('tar -zxf "${PKG_FILE}" -C "${PKG_ROOT}"', script)

    def test_script_checks_existing_config(self):
        script = render_reinstall_master_script(
            deploy_path="/data/dts/test",
            pkg_name="mysql-dts-v2.0.1.tar.gz",
            config_file="dm-master-1.toml",
            dts_node_name="dm-master-1",
        )
        self.assertIn('if [[ ! -f "${CONF_DIR}/dm-master-1.toml" ]]', script)


class ReinstallSubflowIntegrationTest(SimpleTestCase):
    """测试重装子流程编排（不依赖数据库）。"""

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_reinstall_subflow.build_dts_trans_file_kwargs")
    def test_subflow_builds_without_error(self, mock_trans):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_reinstall_subflow import mysql_dts_reinstall_subflow

        mock_trans.return_value = ({"file_list": ["test"]}, "mysql-dts-v2.0.1.tar.gz")

        inp = MysqlDtsReinstallSubflowInput(
            root_id="test-root",
            dts_cluster_id=1,
            bk_biz_id=1,
            bk_cloud_id=0,
            master_addr="127.0.0.2:18301",
            master_nodes=[{"ip": "127.0.0.2", "bk_cloud_id": 0, "name": "dm-master-1"}],
            worker_nodes=[{"ip": "127.0.0.3", "bk_cloud_id": 0, "name": "dm-worker-1"}],
            deploy_path="/data/dts/test",
            force_reinstall=False,
            creator="tester",
        )

        sub = mysql_dts_reinstall_subflow(inp)
        self.assertIsNotNone(sub)
