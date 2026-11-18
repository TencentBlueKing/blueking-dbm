# -*- coding: utf-8 -*-
from contextlib import contextmanager
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.flow.engine.bamboo.scene.spider.spider_layer_disaster_recover_flow import (
    TenDBClusterSpiderLayerDisasterRecoverFlow,
)

MODULE = "backend.flow.engine.bamboo.scene.spider.spider_layer_disaster_recover_flow"
SPIDER_PORT = 25000


class RecordingBuilder:
    instances = []

    def __init__(self, *args, **kwargs):
        self.events = []
        RecordingBuilder.instances.append(self)

    def add_sub_pipeline(self, sub_flow=None, **kwargs):
        self.events.append(sub_flow)

    def add_parallel_sub_pipeline(self, sub_flow_list=None):
        self.events.append(("parallel", sub_flow_list))

    def add_act(self, act_name="", **kwargs):
        self.events.append(act_name)

    def build_sub_process(self, sub_name=""):
        return SimpleNamespace(name=sub_name, events=list(self.events))


def _host(ip):
    return {"ip": ip, "bk_cloud_id": 0, "bk_host_id": 1, "spec": {"id": 1}}


def _cluster():
    proxy = MagicMock()
    proxy.filter.return_value = []
    return SimpleNamespace(
        id=1,
        bk_biz_id=100,
        bk_cloud_id=0,
        immute_domain="spider.spidertest.db",
        proxyinstance_set=proxy,
    )


def _flow(disable_manual_confirm=False):
    return TenDBClusterSpiderLayerDisasterRecoverFlow(
        "root-1",
        {"uid": "u1", "bk_biz_id": 100, "disable_manual_confirm": disable_manual_confirm, "infos": []},
    )


@contextmanager
def _patched_cluster_flow(flow):
    RecordingBuilder.instances = []
    cluster = _cluster()
    flow._add_pre_stage = MagicMock()
    flow._build_cluster_ticket = MagicMock(return_value={"uid": "u1"})
    flow._build_master_install_segment = MagicMock(return_value=SimpleNamespace(name="master-install"))
    flow._build_slave_install_segment = MagicMock(return_value=SimpleNamespace(name="slave-install"))
    flow._build_master_routing_segment = MagicMock(return_value=SimpleNamespace(name="master-route"))
    flow._build_slave_routing_segment = MagicMock(return_value=SimpleNamespace(name="slave-route"))
    flow._build_dns_restore_segment = MagicMock(return_value=SimpleNamespace(name="dns"))
    with (
        patch(f"{MODULE}.Cluster.objects.get", return_value=cluster),
        patch(f"{MODULE}.resolve_spider_ctl_ports", return_value=(SPIDER_PORT, 26000)),
        patch(f"{MODULE}.get_spider_pkg_id_for_layer_disaster_recover", return_value=9),
        patch(f"{MODULE}.resolve_ctl_primary_ip", return_value="127.0.0.21"),
        patch(f"{MODULE}.reduce_spiders_flow", return_value=SimpleNamespace(name="reduce")),
        patch(f"{MODULE}.SubBuilder", RecordingBuilder),
        patch(f"{MODULE}.standardize_mysql_cluster_subflow", side_effect=lambda **kwargs: kwargs),
    ):
        yield


def _names(events):
    names = []
    for event in events:
        if isinstance(event, str):
            names.append(event)
        elif isinstance(event, tuple):
            names.append(event[0])
        else:
            names.append(event.name)
    return names


class SpiderLayerDisasterRecoverStandardizeTest(TestCase):
    def test_standardize_flags_follow_add_spider_nodes(self):
        flow = _flow()
        ticket = {"uid": "u1"}
        cluster = _cluster()
        masters = [_host("127.0.0.11"), _host("127.0.0.12")]
        slaves = [_host("127.0.0.31")]
        RecordingBuilder.instances = []
        with patch(f"{MODULE}.SubBuilder", RecordingBuilder), patch(
            f"{MODULE}.standardize_mysql_cluster_subflow", side_effect=lambda **kwargs: kwargs
        ):
            both = flow._build_new_spider_standardize_segment(
                cluster=cluster,
                master_new=masters,
                slave_new=slaves,
                spider_port=SPIDER_PORT,
                cluster_ticket=ticket,
            )
            slave_only = flow._build_new_spider_standardize_segment(
                cluster=cluster,
                master_new=[],
                slave_new=slaves,
                spider_port=SPIDER_PORT,
                cluster_ticket=ticket,
            )

        self.assertIn("标准化新接入层", both.name)
        master_call, slave_call = both.events
        self.assertEqual(
            master_call["instances"],
            ["127.0.0.11:{}".format(SPIDER_PORT), "127.0.0.12:{}".format(SPIDER_PORT)],
        )
        self.assertFalse(master_call["with_actuator"])
        self.assertTrue(master_call["with_bk_plugin"])
        self.assertTrue(master_call["with_instance_standardize"])
        self.assertTrue(master_call["with_collect_sysinfo"])
        self.assertEqual(master_call["bk_cloud_id"], 0)
        self.assertEqual(master_call["bk_biz_id"], 100)
        self.assertEqual(master_call["data"], ticket)
        self.assertIsNot(master_call["data"], ticket)

        self.assertEqual(slave_call["instances"], ["127.0.0.31:{}".format(SPIDER_PORT)])
        self.assertFalse(slave_call["with_actuator"])
        self.assertFalse(slave_call["with_bk_plugin"])
        self.assertFalse(slave_call["with_instance_standardize"])
        self.assertFalse(slave_call["with_collect_sysinfo"])

        self.assertEqual(len(slave_only.events), 1)
        self.assertEqual(slave_only.events[0]["instances"], ["127.0.0.31:{}".format(SPIDER_PORT)])
        self.assertFalse(slave_only.events[0]["with_bk_plugin"])

    def test_standardize_sits_after_dns_and_before_scale_in_confirm(self):
        flow = _flow()
        info = {
            "cluster_id": 1,
            "spider_master_new_ip_list": [_host("127.0.0.11"), _host("127.0.0.12")],
            "spider_master_old_ip_list": [_host("127.0.0.21"), _host("127.0.0.22")],
            "spider_slave_new_ip_list": [_host("127.0.0.31")],
            "spider_slave_old_ip_list": [_host("127.0.0.41")],
        }
        with _patched_cluster_flow(flow):
            built = flow._cluster_sub_flow(info)

        names = _names(built.events)
        dns_at = names.index("dns")
        std_at = next(index for index, name in enumerate(names) if "标准化新接入层" in name)
        unlock_at = names.index("释放部分单据互斥锁")
        pause_at = names.index("人工确认缩容旧接入层")
        self.assertLess(dns_at, std_at)
        self.assertLess(std_at, unlock_at)
        self.assertLess(unlock_at, pause_at)

        standardize = next(event for event in built.events if getattr(event, "name", "") and "标准化新接入层" in event.name)
        self.assertEqual(
            [call["instances"] for call in standardize.events],
            [
                ["127.0.0.11:{}".format(SPIDER_PORT), "127.0.0.12:{}".format(SPIDER_PORT)],
                ["127.0.0.31:{}".format(SPIDER_PORT)],
            ],
        )
        self.assertFalse(standardize.events[1]["with_instance_standardize"])

    def test_standardize_still_runs_when_manual_confirm_disabled(self):
        flow = _flow(disable_manual_confirm=True)
        info = {
            "cluster_id": 1,
            "spider_slave_new_ip_list": [_host("127.0.0.31")],
            "spider_slave_old_ip_list": [_host("127.0.0.41")],
        }
        with _patched_cluster_flow(flow):
            built = flow._cluster_sub_flow(info)

        names = _names(built.events)
        std_at = next(index for index, name in enumerate(names) if "标准化新接入层" in name)
        unlock_at = names.index("释放部分单据互斥锁")
        self.assertLess(std_at, unlock_at)
        self.assertNotIn("人工确认缩容旧接入层", names)
        standardize = next(event for event in built.events if getattr(event, "name", "") and "标准化新接入层" in event.name)
        self.assertEqual(len(standardize.events), 1)
        self.assertEqual(standardize.events[0]["instances"], ["127.0.0.31:{}".format(SPIDER_PORT)])
        self.assertFalse(standardize.events[0]["with_collect_sysinfo"])
