# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket import MySQLCheckSumTicket


class MysqlChecksumTicketRelatedDoneTest(SimpleTestCase):
    def _execute(self, extra_kwargs=None):
        parent = MagicMock()
        checksum = MagicMock()
        checksum.id = 955
        trans_data = SimpleNamespace()
        kwargs = {
            "uid": 954,
            "created_by": "admin",
            "bk_biz_id": 20,
            "checksum_info": {"ticket_type": "MYSQL_DTS_CHECKSUM", "details": {}},
        }
        kwargs.update(extra_kwargs or {})
        data = MagicMock()
        data.get_one_of_inputs.side_effect = lambda key: {
            "kwargs": kwargs,
            "trans_data": trans_data,
        }.get(key)
        data.outputs = {}

        service = MySQLCheckSumTicket()
        service.log_info = MagicMock()
        with patch(
            "backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket.Ticket"
        ) as mock_ticket_cls:
            mock_ticket_cls.objects.get.return_value = parent
            mock_ticket_cls.create_ticket.return_value = checksum
            self.assertTrue(service._execute(data, parent_data=None))
        return parent, checksum, trans_data

    def test_default_related_ticket_done_false(self):
        parent, checksum, trans_data = self._execute()
        parent.add_related_ticket.assert_called_once_with(checksum, done=False)
        self.assertEqual(trans_data.auto_checksum_ticket_id, 955)

    def test_dts_related_ticket_done_true(self):
        parent, checksum, _ = self._execute(extra_kwargs={"related_ticket_done": True})
        parent.add_related_ticket.assert_called_once_with(checksum, done=True)

    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow.SubBuilder")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow.Cluster")
    @patch("backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow.build_dts_checksum_ticket_info")
    def test_dts_checksum_subflow_uses_default_related_done_false(self, mock_build, mock_cluster, mock_sub_cls):
        from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow import mysql_dts_checksum_subflow
        from backend.flow.utils.mysql.dts.context import MysqlDtsChecksumSubflowInput

        mock_build.return_value = {
            "details": {
                "infos": [
                    {
                        "cluster_id": 1,
                        "master": {"ip": "127.0.0.2", "port": 3306},
                        "slaves": [{"ip": "127.0.0.3", "port": 3306}],
                    }
                ]
            }
        }
        mock_cluster.objects.get.return_value = SimpleNamespace(id=1, bk_cloud_id=0)
        sub = MagicMock()
        mock_sub_cls.return_value = sub
        mysql_dts_checksum_subflow(
            inp=MysqlDtsChecksumSubflowInput(root_id="root", bk_biz_id=1, ticket_id=8, creator="u"),
            task_spec=MagicMock(),
        )
        first_kwargs = sub.add_act.call_args_list[0].kwargs["kwargs"]
        self.assertFalse(first_kwargs.get("related_ticket_done", False))
