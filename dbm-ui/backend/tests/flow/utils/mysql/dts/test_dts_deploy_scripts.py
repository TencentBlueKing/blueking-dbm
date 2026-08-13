# -*- coding: utf-8 -*-
"""
本地验证 DTS 介质解压与 Master/Worker 启动脚本。

依赖开发机存在：/data/install/mysql-dts-v0.0.1.tar.gz
若介质不存在则 skip。

运行（无需完整 Django settings）::

    cd dbm-ui && PYTHONPATH=. .venv/bin/python -m unittest \\
      backend.tests.flow.utils.mysql.dts.test_dts_deploy_scripts -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

# 允许直接 unittest 导入 backend 包（定位到 dbm-ui 目录）
_DBM_UI = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../"))
if _DBM_UI not in sys.path:
    sys.path.insert(0, _DBM_UI)

from jinja2.sandbox import SandboxedEnvironment as Environment  # noqa: E402

from backend.flow.utils.mysql.dts.script_template import (  # noqa: E402
    start_mysql_dts_master_template,
    start_mysql_dts_worker_template,
    stop_mysql_dts_process_template,
)

PKG_NAME = "mysql-dts-v0.0.1.tar.gz"
PKG_PATH = f"/data/install/{PKG_NAME}"
ADVERTISE_IP = "127.0.0.1"
MASTER_PORT = 18301
MASTER_PEER_PORT = 18401
WORKER_PORT = 18501


def _render_master_config(deploy_path: str, node_name: str) -> str:
    data_dir = f"{deploy_path}/{node_name}-data"
    log_file = f"{deploy_path}/{node_name}.log"
    peer_url = f"http://{ADVERTISE_IP}:{MASTER_PEER_PORT}"
    return f"""# dm-master.toml
name = "{node_name}"
master-addr = "{ADVERTISE_IP}:{MASTER_PORT}"
peer-urls = "{peer_url}"
initial-cluster = "{node_name}={peer_url}"
data-dir = "{data_dir}"
log-file = "{log_file}"
log-level = "info"
log-rotate = "1d"
openapi = true
"""


def _render_worker_config(deploy_path: str, node_name: str, master_addr: str) -> str:
    relay_dir = f"{deploy_path}/{node_name}-data"
    log_file = f"{deploy_path}/{node_name}.log"
    return f"""# dm-worker.toml
name = "{node_name}"
worker-addr = "{ADVERTISE_IP}:{WORKER_PORT}"
join = "{master_addr}"
relay-dir = "{relay_dir}"
log-file = "{log_file}"
log-level = "info"
log-rotate = "1d"
"""


@unittest.skipUnless(os.path.isfile(PKG_PATH), f"missing local DTS package: {PKG_PATH}")
class DtsDeployScriptLocalTest(unittest.TestCase):
    """用真实介质包校验解压布局与本地启停。"""

    def setUp(self):
        self.deploy_path = tempfile.mkdtemp(prefix="dts-local-test-")
        self.env = Environment()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        stop_script = self.env.from_string(stop_mysql_dts_process_template).render(deploy_path=self.deploy_path)
        subprocess.run(["bash", "-c", stop_script], check=False, capture_output=True, text=True)
        time.sleep(1)
        shutil.rmtree(self.deploy_path, ignore_errors=True)

    def _run_bash(self, script: str):
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        if result.returncode != 0:
            self.fail(
                f"script failed rc={result.returncode}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}\n"
                f"script:\n{script}"
            )
        return result

    def test_extract_puts_binaries_under_deploy_bin_not_bin_bin(self):
        """解压后二进制应在 deploy_path/bin/，而不是 deploy_path/bin/bin/。"""
        bin_dir = os.path.join(self.deploy_path, "bin")
        os.makedirs(self.deploy_path, exist_ok=True)
        extract = f"""
set -euo pipefail
if ! tar -zxf "{PKG_PATH}" -C "{self.deploy_path}" --strip-components=1 2>/dev/null; then
  tar -xf "{PKG_PATH}" -C "{self.deploy_path}" --strip-components=1
fi
"""
        self._run_bash(extract)

        self.assertTrue(os.path.isfile(os.path.join(bin_dir, "dm-master")))
        self.assertTrue(os.path.isfile(os.path.join(bin_dir, "dm-worker")))
        self.assertTrue(os.path.isfile(os.path.join(bin_dir, "dmctl")))
        self.assertFalse(
            os.path.isdir(os.path.join(bin_dir, "bin")),
            "unexpected nested bin/bin layout after extract",
        )

    def test_wrong_extract_to_bin_dir_creates_nested_bin(self):
        """回归：解到 bin/ 再 strip 一层会得到 bin/bin（旧实现缺陷）。"""
        bin_dir = os.path.join(self.deploy_path, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrong = f"""
set -euo pipefail
tar -zxf "{PKG_PATH}" -C "{bin_dir}" --strip-components=1
"""
        self._run_bash(wrong)
        self.assertTrue(os.path.isfile(os.path.join(bin_dir, "bin", "dm-master")))
        self.assertFalse(os.path.isfile(os.path.join(bin_dir, "dm-master")))

    def test_rendered_start_scripts_can_boot_master_and_worker(self):
        """渲染正式启动脚本，本地拉起 Master + Worker 后再停掉。"""
        master_name = "dm-master-0"
        worker_name = "dm-worker-1"
        master_config_file = f"{master_name}.toml"
        worker_config_file = f"{worker_name}.toml"
        master_addr = f"{ADVERTISE_IP}:{MASTER_PORT}"

        conf_dir = os.path.join(self.deploy_path, "conf")
        os.makedirs(conf_dir, exist_ok=True)
        with open(os.path.join(conf_dir, master_config_file), "w", encoding="utf-8") as fp:
            fp.write(_render_master_config(self.deploy_path, master_name))
        with open(os.path.join(conf_dir, worker_config_file), "w", encoding="utf-8") as fp:
            fp.write(_render_worker_config(self.deploy_path, worker_name, master_addr))

        master_script = self.env.from_string(start_mysql_dts_master_template).render(
            deploy_path=self.deploy_path,
            pkg_name=PKG_NAME,
            config_file=master_config_file,
            dts_node_name=master_name,
            listen_port=MASTER_PORT,
        )
        worker_script = self.env.from_string(start_mysql_dts_worker_template).render(
            deploy_path=self.deploy_path,
            pkg_name=PKG_NAME,
            config_file=worker_config_file,
            dts_node_name=worker_name,
            listen_port=WORKER_PORT,
        )

        self._run_bash(master_script)
        self._run_bash(worker_script)

        bin_dir = os.path.join(self.deploy_path, "bin")
        self.assertTrue(os.path.isfile(os.path.join(bin_dir, "dm-master")))
        self.assertFalse(os.path.isdir(os.path.join(bin_dir, "bin")))

        master_pgrep = subprocess.run(
            ["pgrep", "-f", f"{bin_dir}/dm-master"],
            capture_output=True,
            text=True,
        )
        worker_pgrep = subprocess.run(
            ["pgrep", "-f", f"{bin_dir}/dm-worker"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(master_pgrep.returncode, 0, "dm-master process not found")
        self.assertEqual(worker_pgrep.returncode, 0, "dm-worker process not found")


class DtsCleanupCacheScriptTest(unittest.TestCase):
    """不依赖本地介质包：锁定 relay / dump 清理脚本内容。"""

    def test_ticket_dump_script_only_named_task_dirs(self):
        from backend.flow.utils.mysql.dts.constants import get_full_migrate_data_dir
        from backend.flow.utils.mysql.dts.script_template import render_clean_ticket_dump_script

        dump_dir = get_full_migrate_data_dir("dts-prod", "t1")
        script = render_clean_ticket_dump_script([dump_dir])
        self.assertIn(dump_dir, script)
        self.assertNotIn("other-task", script)
        self.assertNotIn("/data/dbbak", script)

    def test_cluster_script_contains_worker_data_and_exported_data(self):
        from backend.flow.utils.mysql.dts.script_template import render_clean_cluster_relay_and_dump_script

        script = render_clean_cluster_relay_and_dump_script(
            "/custom/dts",
            ["dm-worker-1", "dm-worker-2"],
            extra_exported_data_dirs=["/data/dts/dts-prod/exported_data"],
        )
        self.assertIn("/custom/dts/dm-worker-1-data", script)
        self.assertIn("/custom/dts/dm-worker-2-data", script)
        self.assertIn("/custom/dts/exported_data", script)
        self.assertIn("/data/dts/dts-prod/exported_data", script)
        self.assertNotIn("/data/dbbak/", script)

    def test_cluster_script_missing_dirs_is_success(self):
        from backend.flow.utils.mysql.dts.script_template import render_clean_cluster_relay_and_dump_script

        missing = tempfile.mkdtemp(prefix="dts-already-gone-")
        os.rmdir(missing)
        script = render_clean_cluster_relay_and_dump_script(
            missing,
            ["dm-worker-1"],
            extra_exported_data_dirs=[f"{missing}-exported"],
        )
        completed = subprocess.run(["bash", "-s"], input=script, text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("if [[ -e", script)


if __name__ == "__main__":
    unittest.main()
