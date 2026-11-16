# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.mysql_os_init import (
    CleanDataBakDirSvr,
    CleanDbExporterSvr,
)
from backend.utils.string import base64_decode

OS_INIT = "backend.flow.plugins.components.collections.mysql.mysql_os_init"


def _service(cls):
    service = cls()
    service.log_info = MagicMock()
    service.log_error = MagicMock()
    return service


def _data(kwargs):
    data = MagicMock()
    data.get_one_of_inputs.side_effect = lambda key: kwargs if key == "kwargs" else None
    return data


def _machine(storage_ports=None, proxy_ports=None):
    machine = MagicMock()
    machine.storageinstance_set.all.return_value = [SimpleNamespace(port=port) for port in storage_ports or []]
    machine.proxyinstance_set.all.return_value = [SimpleNamespace(port=port) for port in proxy_ports or []]
    return machine


def _patch_machine(machine):
    query = MagicMock()
    query.prefetch_related.return_value.first.return_value = machine
    return patch(f"{OS_INIT}.Machine.objects.filter", return_value=query)


def _script_of(mock_job):
    body = mock_job.fast_execute_script.call_args.args[0]
    return base64_decode(body["script_content"])


class CleanDbExporterSvrTest(SimpleTestCase):
    def test_script_kills_exporter_and_skips_bak_cleanup_when_machine_missing(self):
        service = _service(CleanDbExporterSvr)
        data = _data({"exec_ip": "127.0.0.2", "bk_cloud_id": 0})
        with _patch_machine(None), patch(f"{OS_INIT}.JobApi") as mock_job:
            mock_job.fast_execute_script.return_value = {"data": {"job_instance_id": 1}}
            self.assertTrue(service._execute(data, None))
        script = _script_of(mock_job)
        self.assertIn("db.*exporter", script)
        self.assertNotIn("mysqllog", script)
        self.assertNotIn("dbbak", script)
        self.assertEqual(data.outputs.exec_ips, ["127.0.0.2"])

    def test_script_runs_when_machine_has_no_instances(self):
        service = _service(CleanDbExporterSvr)
        data = _data({"exec_ip": "127.0.0.3", "bk_cloud_id": 0})
        with _patch_machine(_machine()), patch(f"{OS_INIT}.JobApi") as mock_job:
            mock_job.fast_execute_script.return_value = {"data": {"job_instance_id": 2}}
            self.assertTrue(service._execute(data, None))
        self.assertIn("db.*exporter", _script_of(mock_job))

    def test_refuses_when_storage_or_proxy_instance_remains(self):
        for machine in (_machine(storage_ports=[20000]), _machine(proxy_ports=[10000])):
            service = _service(CleanDbExporterSvr)
            data = _data({"exec_ip": "127.0.0.4", "bk_cloud_id": 0})
            with _patch_machine(machine), patch(f"{OS_INIT}.JobApi") as mock_job:
                with self.assertRaises(Exception) as raised:
                    service._execute(data, None)
            self.assertIn("拒绝执行备份目录清理", str(raised.exception))
            mock_job.fast_execute_script.assert_not_called()


class CleanDataBakDirSvrTest(SimpleTestCase):
    def test_script_keeps_bak_cleanup_and_drops_exporter_loop(self):
        service = _service(CleanDataBakDirSvr)
        data = _data({"exec_ip": "127.0.0.2", "bk_cloud_id": 0, "root_id": "root-exercise"})
        with _patch_machine(None), patch(f"{OS_INIT}.JobApi") as mock_job:
            mock_job.fast_execute_script.return_value = {"data": {"job_instance_id": 3}}
            self.assertTrue(service._execute(data, None))
        script = _script_of(mock_job)
        self.assertNotIn("db.*exporter", script)
        self.assertIn("检测到 mysqld 进程，拒绝清理备份目录", script)
        self.assertIn("mysqllog", script)
        self.assertIn("dbbak", script)
