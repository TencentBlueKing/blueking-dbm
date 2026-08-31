# -*- coding: utf-8 -*-
"""注册 DTS 集群元数据须把 trans_data 写回 outputs（同层 sibling 才能合并）。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.dts.deploy.register_meta import (
    MysqlDtsRegisterClusterMetaService,
)
from backend.flow.utils.mysql.dts.constants import DtsRegisterMode
from backend.flow.utils.mysql.dts.context import MysqlDtsTransData


class MysqlDtsRegisterClusterMetaOutputTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsRegisterClusterMetaService()
        service.log_info = MagicMock()
        return service

    def test_create_outputs_trans_data(self):
        trans_data = MysqlDtsTransData()
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "bk_biz_id": 20,
                "bk_cloud_id": 0,
                "cluster_name": "dts-ut",
                "master_nodes": [{"ip": "127.0.0.2"}],
                "worker_nodes": [{"ip": "127.0.0.3"}],
                "master_addr": "127.0.0.2:8261",
                "deploy_path": "/data/dts",
                "creator": "tester",
            },
            "trans_data": trans_data,
        }.get(key)
        data.outputs = MagicMock()
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.deploy.register_meta.create",
            return_value=SimpleNamespace(id=13),
        ) as mock_create:
            ok = self._make_service()._execute(data, parent_data=None)
        self.assertTrue(ok)
        self.assertEqual(trans_data.migrate_context.dts_cluster_id, 13)
        self.assertNotIn("ticket_id", mock_create.call_args.kwargs)
        data.outputs.__setitem__.assert_any_call("trans_data", trans_data)

    def test_append_worker_outputs_trans_data(self):
        trans_data = MysqlDtsTransData()
        trans_data.migrate_context.dts_cluster_id = 13
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": {
                "register_mode": DtsRegisterMode.APPEND_WORKER.value,
                "dts_cluster_id": 13,
                "new_worker_nodes": [{"ip": "127.0.0.4"}],
                "creator": "tester",
            },
            "trans_data": trans_data,
        }.get(key)
        data.outputs = MagicMock()
        with patch(
            "backend.db_meta.api.cluster.mysqldts.append_worker_nodes",
        ):
            ok = self._make_service()._execute(data, parent_data=None)
        self.assertTrue(ok)
        data.outputs.__setitem__.assert_any_call("trans_data", trans_data)
