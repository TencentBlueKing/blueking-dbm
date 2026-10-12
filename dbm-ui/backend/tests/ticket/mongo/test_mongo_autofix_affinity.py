# -*- coding: utf-8 -*-
"""MongoDB 自愈替换：同反亲和组一次申请，并带上存活机器。"""

import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.utils import timezone

from backend.configuration.constants import AffinityEnum
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_services.mongodb.autofix.enums import MongoAutofixConfirmResult, MongoAutofixStatus
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    GROUP_WAIT_MINUTES,
    _core_is_untriaged,
    _core_needs_replace_slot,
    _merge_connected_shard_groups,
    ensure_affinity_groups,
    survivor_current_hosts,
)
from backend.ticket.builders.mongodb.mongo_autofix import (
    MongoDBAutofixResourceParamBuilder,
    assign_applied_hosts,
    iter_replace_groups,
)


def _host(ip, spec_id=1, group="shard:9:s1", bk_host_id=None):
    return {
        "ip": ip,
        "spec_id": spec_id,
        "bk_host_id": bk_host_id or int(ip.split(".")[-1]),
        "affinity_group": group,
        "spec_config": {"id": spec_id},
        "labels": ["3"],
        "label_names": ["cyc"],
    }


class TestReplaceGroups:
    def test_same_group_and_spec_is_one_apply(self):
        hosts = [_host("127.0.0.2"), _host("127.0.0.1")]
        groups = list(iter_replace_groups(hosts))
        assert len(groups) == 1
        key, members = groups[0]
        assert key == "replace-1-shard:9:s1"
        assert [item["ip"] for item in members] == ["127.0.0.1", "127.0.0.2"]

    def test_different_shard_or_spec_splits(self):
        hosts = [
            _host("127.0.0.1", group="shard:9:s1"),
            _host("127.0.0.2", group="shard:9:s2"),
            _host("127.0.0.3", spec_id=8, group="shard:9:s1"),
        ]
        keys = [key for key, _ in iter_replace_groups(hosts)]
        assert len(keys) == 3

    def test_assign_applied_hosts_back_to_fault_ip(self):
        info = {
            "mongod_list": [_host("127.0.0.2"), _host("127.0.0.1")],
            "mongos_list": [],
            "replace-1-shard:9:s1": [{"ip": "127.0.0.11"}, {"ip": "127.0.0.12"}],
        }
        assign_applied_hosts(info)
        assert info["127.0.0.1"] == [{"ip": "127.0.0.11"}]
        assert info["127.0.0.2"] == [{"ip": "127.0.0.12"}]


class TestReplaceAffinitySpec:
    def test_count_and_current_hosts_without_pinning_fault_zone(self):
        hosts = [_host("127.0.0.1", bk_host_id=11), _host("127.0.0.2", bk_host_id=12)]
        info = {
            "cluster_ids": [9],
            "bk_biz_id": 3,
            "mongod_list": hosts,
            "mongos_list": [],
            "prior_current_hosts": [
                {"ip": "127.0.0.99", "bk_host_id": 99, "sub_zone": "sz", "sub_zone_id": "3", "rack_id": "7"}
            ],
            "resource_spec": {},
        }
        cluster = SimpleNamespace(
            id=9,
            bk_cloud_id=0,
            region="深圳",
            disaster_tolerance_level=AffinityEnum.CROSS_SUBZONE_STRONG,
            zone_list=[5, 6],
        )
        builder = MongoDBAutofixResourceParamBuilder.__new__(MongoDBAutofixResourceParamBuilder)
        builder.ticket = SimpleNamespace(bk_biz_id=3)
        builder.ticket_data = {"infos": [info]}
        survivors = [{"ip": "127.0.0.8", "bk_host_id": 8, "sub_zone": "a", "sub_zone_id": "1", "rack_id": "2"}]
        with patch(
            "backend.ticket.builders.mongodb.mongo_autofix.Cluster.objects.filter", return_value=[cluster]
        ), patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.survivor_current_hosts",
            return_value=survivors,
        ):
            builder.patch_replace_affinity()
        spec = info["resource_spec"]["replace-1-shard:9:s1"]
        assert spec["count"] == 2
        assert spec["affinity"] == AffinityEnum.CROSS_SUBZONE_STRONG
        assert spec["tolerance"] == 0.33
        assert spec["location_spec"] == {"city": "深圳", "sub_zone_ids": [5, 6]}
        assert "include_or_exclue" not in spec["location_spec"]
        assert [item["bk_host_id"] for item in spec["current_hosts"]] == [8, 99]


class TestGroupSlot:
    def test_confirmed_replace_without_ticket_joins(self):
        core = SimpleNamespace(id=2, confirm_result=MongoAutofixConfirmResult.MACHINE_DEAD.value, ticket_id=-1)
        assert _core_needs_replace_slot(core, 1) is True

    def test_untriaged_pre_does_not_join_and_blocks_execute(self):
        core = SimpleNamespace(
            id=2,
            confirm_result="",
            ticket_id=-1,
            deal_status=MongoAutofixStatus.PRE_RUNNING.value,
            update_at=timezone.now(),
        )
        assert _core_needs_replace_slot(core, 1) is False
        assert _core_is_untriaged(core) is True

    def test_stale_untriaged_no_longer_blocks(self):
        core = SimpleNamespace(
            id=2,
            confirm_result="",
            ticket_id=-1,
            deal_status=MongoAutofixStatus.PRE_RUNNING.value,
            update_at=timezone.now() - datetime.timedelta(minutes=GROUP_WAIT_MINUTES + 1),
        )
        assert _core_is_untriaged(core) is False

    def test_current_core_always_occupies_a_slot(self):
        core = SimpleNamespace(id=1, confirm_result="", ticket_id=-1)
        assert _core_needs_replace_slot(core, 1) is True


class TestMultiShardAffinity:
    def test_intersecting_shard_hosts_share_one_group(self):
        merged = _merge_connected_shard_groups(
            [
                (1, frozenset({"s1", "s2"})),
                (2, frozenset({"s2", "s3"})),
                (3, frozenset({"s9"})),
            ]
        )
        assert merged[1] == frozenset({"s1", "s2", "s3"})
        assert merged[2] == frozenset({"s1", "s2", "s3"})
        assert merged[3] == frozenset({"s9"})

    def test_ensure_affinity_groups_merges_connected_hosts(self):
        cluster = SimpleNamespace(id=9, cluster_type=ClusterType.MongoShardedCluster.value)
        hosts = [
            {"ip": "127.0.0.1", "bk_host_id": 1, "machine_type": MachineType.MONGODB.value, "affinity_group": "old"},
            {"ip": "127.0.0.2", "bk_host_id": 2, "machine_type": MachineType.MONGODB.value},
            {"ip": "127.0.0.3", "bk_host_id": 3, "machine_type": MachineType.MONGODB.value},
        ]
        cluster_qs = SimpleNamespace(first=lambda: cluster)
        with patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.Cluster.objects.filter",
            return_value=cluster_qs,
        ), patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket._shard_names_by_host",
            return_value={
                1: frozenset({"s1", "s2"}),
                2: frozenset({"s2", "s3"}),
                3: frozenset({"s9"}),
            },
        ):
            ensure_affinity_groups(9, [], hosts)
        assert hosts[0]["affinity_group"] == "shard:9:s1,s2,s3"
        assert hosts[1]["affinity_group"] == "shard:9:s1,s2,s3"
        assert hosts[2]["affinity_group"] == "shard:9:s9"

    def test_survivor_current_hosts_only_covers_group_shards(self):
        cluster = SimpleNamespace(id=9)
        machines = {
            8: SimpleNamespace(
                ip="127.0.0.8",
                bk_host_id=8,
                bk_sub_zone="a",
                bk_sub_zone_id=1,
                bk_rack_id=2,
                machine_type=MachineType.MONGODB.value,
            ),
            9: SimpleNamespace(
                ip="127.0.0.9",
                bk_host_id=9,
                bk_sub_zone="b",
                bk_sub_zone_id=2,
                bk_rack_id=3,
                machine_type=MachineType.MONGODB.value,
            ),
            10: SimpleNamespace(
                ip="127.0.0.10",
                bk_host_id=10,
                bk_sub_zone="c",
                bk_sub_zone_id=3,
                bk_rack_id=4,
                machine_type=MachineType.MONGODB.value,
            ),
        }
        insts = [
            SimpleNamespace(id=101, machine=machines[8]),
            SimpleNamespace(id=102, machine=machines[9]),
            SimpleNamespace(id=103, machine=machines[10]),
        ]
        storage_qs = SimpleNamespace(filter=lambda **_kwargs: insts)
        with patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.StorageInstance.objects.select_related",
            return_value=storage_qs,
        ), patch(
            "backend.db_services.mongodb.autofix.mongodb_autofix_ticket.MongoDBListRetrieveResource.query_storage_shard",
            return_value=(None, {101: "s1", 102: "s2", 103: "s9"}),
        ):
            survivors = survivor_current_hosts(cluster, "shard:9:s1,s2,s3", fault_host_ids={1, 2})
        assert sorted(item["bk_host_id"] for item in survivors) == [8, 9]
