# -*- coding: utf-8 -*-
"""prepare_user：账号入上下文，并在 migrate 层解析 DTS 集群主键。"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.dts.migrate.prepare_user import (
    MysqlDtsPrepareMigrateUserService,
)
from backend.flow.utils.mysql.dts.context import MysqlDtsTransData


def _cluster(**overrides):
    cluster = SimpleNamespace(
        id=11,
        name="dts-migrate-18801",
        master_addr="127.0.0.2:8261",
        bk_cloud_id=0,
    )
    for key, value in overrides.items():
        setattr(cluster, key, value)
    return cluster


class MysqlDtsPrepareMigrateUserServiceTest(SimpleTestCase):
    def _make_service(self):
        service = MysqlDtsPrepareMigrateUserService()
        service.log_info = MagicMock()
        service.log_error = MagicMock()
        return service

    def _run(self, *, cluster, kwargs_extra=None):
        trans_data = MysqlDtsTransData()
        kwargs = {
            "dts_user": "dts_u",
            "dts_password": "pwd",
            "grant_hosts": ["127.0.0.1"],
            "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.2:3306"}],
            "bk_biz_id": 20,
            "dts_cluster_id": None,
            "cluster_name": "dts-migrate-18801",
        }
        kwargs.update(kwargs_extra or {})
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {"kwargs": kwargs, "trans_data": trans_data}.get(key)
        data.outputs = {}
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.prepare_user.load_active_dts_cluster",
            return_value=cluster,
        ) as mock_load:
            ok = self._make_service()._execute(data, parent_data=None)
        return ok, data, trans_data, mock_load

    def test_name_lookup_writes_cluster_id(self):
        ok, data, trans_data, mock_load = self._run(cluster=_cluster())
        self.assertTrue(ok)
        mock_load.assert_called_once_with(dts_cluster_id=None, bk_biz_id=20, cluster_name="dts-migrate-18801")
        self.assertEqual(trans_data.migrate_context.dts_cluster_id, 11)
        self.assertEqual(trans_data.migrate_context.cluster_name, "dts-migrate-18801")
        self.assertEqual(trans_data.migrate_context.master_addr, "127.0.0.2:8261")
        self.assertEqual(trans_data.migrate_context.dts_user, "dts_u")
        self.assertIs(data.outputs["trans_data"], trans_data)

    def test_id_lookup_for_use_existing(self):
        ok, unused_data, trans_data, mock_load = self._run(
            cluster=_cluster(id=9, name="dts-exist"),
            kwargs_extra={"dts_cluster_id": 9, "cluster_name": ""},
        )
        self.assertTrue(ok)
        mock_load.assert_called_once_with(dts_cluster_id=9, bk_biz_id=20, cluster_name="")
        self.assertEqual(trans_data.migrate_context.dts_cluster_id, 9)

    def test_context_cluster_id_not_used(self):
        trans_data = MysqlDtsTransData()
        trans_data.migrate_context.dts_cluster_id = 7
        trans_data.migrate_context.cluster_name = "from-context"
        kwargs = {
            "dts_user": "dts_u",
            "dts_password": "pwd",
            "grant_hosts": ["127.0.0.1"],
            "grant_targets": [{"bk_cloud_id": 0, "address": "127.0.0.2:3306"}],
            "bk_biz_id": 20,
            "dts_cluster_id": None,
            "cluster_name": "dts-migrate-18801",
        }
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {"kwargs": kwargs, "trans_data": trans_data}.get(key)
        data.outputs = {}
        with patch(
            "backend.flow.plugins.components.collections.mysql.dts.migrate.prepare_user.load_active_dts_cluster",
            return_value=_cluster(),
        ) as mock_load:
            ok = self._make_service()._execute(data, parent_data=None)
        self.assertTrue(ok)
        mock_load.assert_called_once_with(dts_cluster_id=None, bk_biz_id=20, cluster_name="dts-migrate-18801")

    def test_missing_cluster_fails_without_writing_account(self):
        ok, unused_data, trans_data, unused_load = self._run(cluster=None)
        self.assertFalse(ok)
        self.assertIsNone(trans_data.migrate_context.dts_cluster_id)
        self.assertEqual(trans_data.migrate_context.dts_user, "")
