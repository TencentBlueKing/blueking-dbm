# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.flow.consts import TDBCTL_USER
from backend.flow.plugins.components.collections.mysql.drop_user import DropUserComponent
from backend.tests.flow.engine.bamboo.scene.spider.test_spider_layer_disaster_recover_standardize import (
    _flow,
    _host,
    _patched_cluster_flow,
)

MODULE = "backend.flow.engine.bamboo.scene.spider.spider_layer_disaster_recover_flow"
SPIDER_PORT = 25000


class RecordingSeg:
    def __init__(self):
        self.events = []

    def add_sub_pipeline(self, sub_flow=None, **kwargs):
        self.events.append(("sub", sub_flow))

    def add_act(self, act_name="", act_component_code="", kwargs=None, **rest):
        self.events.append(("act", act_name, act_component_code, kwargs or {}))


def _cluster():
    return SimpleNamespace(id=1, bk_cloud_id=0)


def _backup_handler(backup_info):
    handler = MagicMock()
    handler.deadlines_days = 7
    handler.get_tendbcluster_spider_layer_grant_priv_backup_info.return_value = backup_info
    return handler


def _drop_acts(events):
    return [event for event in events if event[0] == "act" and event[2] == DropUserComponent.code]


class SpiderLayerDisasterRecoverDropSpiderUserTest(TestCase):
    def test_priv_recover_then_drops_spider_at_old_master_ips(self):
        flow = _flow()
        seg = RecordingSeg()
        missing = {"priv_backup_missing": False}
        priv = SimpleNamespace(name="priv")
        handler = _backup_handler({"priv_files": ["grant.sql"], "task_ids": ["task-1"]})
        with (
            patch(f"{MODULE}.MySQLBackupHandler", return_value=handler),
            patch(f"{MODULE}.spider_layer_priv_recover_sub_flow", return_value=priv),
        ):
            flow._maybe_add_priv_recover(
                seg=seg,
                cluster=_cluster(),
                info={},
                target_role="spider_master",
                restore_ips=["127.0.0.11", "127.0.0.12"],
                spider_port=SPIDER_PORT,
                priv_backup_missing=missing,
                drop_hosts=["127.0.0.21", "127.0.0.22"],
            )

        self.assertEqual(seg.events[0], ("sub", priv))
        drops = _drop_acts(seg.events)
        self.assertEqual(
            [(item[3]["address"], item[3]["host"]) for item in drops],
            [
                ("127.0.0.11:{}".format(SPIDER_PORT), "127.0.0.21"),
                ("127.0.0.11:{}".format(SPIDER_PORT), "127.0.0.22"),
                ("127.0.0.12:{}".format(SPIDER_PORT), "127.0.0.21"),
                ("127.0.0.12:{}".format(SPIDER_PORT), "127.0.0.22"),
            ],
        )
        for _kind, _name, _code, kwargs in drops:
            self.assertEqual(kwargs["user"], TDBCTL_USER)
            self.assertEqual(kwargs["bk_cloud_id"], 0)
            self.assertTrue(kwargs["ignore_errors"])
            self.assertNotIn("disable_binlog", kwargs)
            self.assertNotIn("primary_tdbctl", kwargs)
        self.assertFalse(missing["priv_backup_missing"])

    def test_no_drop_when_drop_hosts_empty(self):
        flow = _flow()
        seg = RecordingSeg()
        handler = _backup_handler({"priv_files": ["grant.sql"], "task_ids": ["task-1"]})
        with (
            patch(f"{MODULE}.MySQLBackupHandler", return_value=handler),
            patch(f"{MODULE}.spider_layer_priv_recover_sub_flow", return_value=SimpleNamespace(name="priv")),
        ):
            flow._maybe_add_priv_recover(
                seg=seg,
                cluster=_cluster(),
                info={},
                target_role="spider_slave",
                restore_ips=["127.0.0.31"],
                spider_port=SPIDER_PORT,
                priv_backup_missing={"priv_backup_missing": False},
                drop_hosts=[],
            )

        self.assertEqual(len(seg.events), 1)
        self.assertEqual(seg.events[0][0], "sub")
        self.assertEqual(_drop_acts(seg.events), [])

    def test_no_drop_when_priv_subflow_absent(self):
        flow = _flow()
        seg = RecordingSeg()
        handler = _backup_handler({"priv_files": ["grant.sql"], "task_ids": ["task-1"]})
        with (
            patch(f"{MODULE}.MySQLBackupHandler", return_value=handler),
            patch(f"{MODULE}.spider_layer_priv_recover_sub_flow", return_value=None),
        ):
            flow._maybe_add_priv_recover(
                seg=seg,
                cluster=_cluster(),
                info={},
                target_role="spider_master",
                restore_ips=["127.0.0.11"],
                spider_port=SPIDER_PORT,
                priv_backup_missing={"priv_backup_missing": False},
                drop_hosts=["127.0.0.21"],
            )

        self.assertEqual(seg.events, [])

    def test_no_drop_when_backup_missing(self):
        flow = _flow()
        seg = RecordingSeg()
        missing = {"priv_backup_missing": False}
        handler = _backup_handler(None)
        with (
            patch(f"{MODULE}.MySQLBackupHandler", return_value=handler),
            patch(f"{MODULE}.spider_layer_priv_recover_sub_flow") as priv_sub,
        ):
            flow._maybe_add_priv_recover(
                seg=seg,
                cluster=_cluster(),
                info={},
                target_role="spider_master",
                restore_ips=["127.0.0.11"],
                spider_port=SPIDER_PORT,
                priv_backup_missing=missing,
                drop_hosts=["127.0.0.21"],
            )

        self.assertEqual(seg.events, [])
        self.assertTrue(missing["priv_backup_missing"])
        priv_sub.assert_not_called()

    def test_no_drop_when_privilege_mode_skips_grant_backup(self):
        flow = _flow()
        seg = RecordingSeg()
        missing = {"priv_backup_missing": False}
        with patch(f"{MODULE}.MySQLBackupHandler") as handler_cls:
            flow._maybe_add_priv_recover(
                seg=seg,
                cluster=_cluster(),
                info={"privilege_recovery_mode": "account_rules_only"},
                target_role="spider_master",
                restore_ips=["127.0.0.11"],
                spider_port=SPIDER_PORT,
                priv_backup_missing=missing,
                drop_hosts=["127.0.0.21"],
            )

        self.assertEqual(seg.events, [])
        self.assertFalse(missing["priv_backup_missing"])
        handler_cls.assert_not_called()

    def test_cluster_flow_passes_old_masters_except_new_masters(self):
        flow = _flow(disable_manual_confirm=True)
        info = {
            "cluster_id": 1,
            "spider_master_new_ip_list": [_host("127.0.0.11"), _host("127.0.0.12")],
            "spider_master_old_ip_list": [_host("127.0.0.21"), _host("127.0.0.11"), _host("127.0.0.22")],
            "spider_slave_new_ip_list": [_host("127.0.0.31")],
            "spider_slave_old_ip_list": [_host("127.0.0.41")],
        }
        with _patched_cluster_flow(flow):
            flow._cluster_sub_flow(info)

        expected = ["127.0.0.21", "127.0.0.22"]
        self.assertEqual(flow._build_master_routing_segment.call_args.kwargs["drop_hosts"], expected)
        self.assertEqual(flow._build_slave_routing_segment.call_args.kwargs["drop_hosts"], expected)

    def test_slave_only_passes_empty_drop_hosts(self):
        flow = _flow(disable_manual_confirm=True)
        info = {
            "cluster_id": 1,
            "spider_slave_new_ip_list": [_host("127.0.0.31")],
            "spider_slave_old_ip_list": [_host("127.0.0.41")],
        }
        with _patched_cluster_flow(flow):
            flow._cluster_sub_flow(info)

        flow._build_master_routing_segment.assert_not_called()
        self.assertEqual(flow._build_slave_routing_segment.call_args.kwargs["drop_hosts"], [])
