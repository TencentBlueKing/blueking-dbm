# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler


class RemoteServiceSystemFilterTest(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.handler = RemoteServiceHandler(bk_biz_id=1)
        self.cluster_handler = SimpleNamespace(cluster=SimpleNamespace(bk_cloud_id=0))

    def _query_side_effect(self, _bk_cloud_id, _address, _cmds, key):
        self.commands = _cmds
        return {_cmds[0]: ["test"], _cmds[1]: []}

    def test_pattern_query_excludes_test_by_default(self):
        with (
            patch.object(
                self.handler,
                "_get_cluster_address",
                return_value=(self.cluster_handler, "127.0.0.1:3306"),
            ),
            patch.object(self.handler, "_get_db_table_list", side_effect=self._query_side_effect),
        ):
            self.handler.show_database_with_pattern(1, ["test"], [])

        excluded_system_dbs = self.commands[0].split("not in", 1)[1]
        self.assertIn("'test'", excluded_system_dbs)

    def test_pattern_query_can_keep_exact_test(self):
        with (
            patch.object(
                self.handler,
                "_get_cluster_address",
                return_value=(self.cluster_handler, "127.0.0.1:3306"),
            ),
            patch.object(self.handler, "_get_db_table_list", side_effect=self._query_side_effect),
        ):
            databases = self.handler.show_database_with_pattern(1, ["test"], [], keep_system_dbs=["test"])

        self.assertEqual(databases, ["test"])
        excluded_system_dbs = self.commands[0].split("not in", 1)[1]
        self.assertNotIn("'test'", excluded_system_dbs)
        self.assertIn("'mysql'", excluded_system_dbs)
