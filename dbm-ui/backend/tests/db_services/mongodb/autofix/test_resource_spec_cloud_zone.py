# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.db_services.mongodb.autofix import mongodb_autofix_ticket as ticket_module
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import (
    _pick_dominant_cloud_zone,
    _sub_zone_ids_of_cloud_zone,
    mongod_get_resource_spec,
    mongos_get_resource_spec,
)


def _machine(ip: str, cloud_zone: str, subzone_id: int):
    return SimpleNamespace(machine=SimpleNamespace(ip=ip, bk_cloud_zone=cloud_zone, bk_sub_zone_id=subzone_id))


def _cluster(instances):
    qs = MagicMock()
    qs.select_related.return_value.all.return_value = instances
    return SimpleNamespace(proxyinstance_set=qs, storageinstance_set=qs)


def _host(ip: str):
    return {"ip": ip, "spec_id": 1, "spec_config": {}, "city": "shenzhen", "labels": [], "label_names": []}


def test_pick_dominant_cloud_zone_returns_zone_over_half():
    assert _pick_dominant_cloud_zone({"cz-a": 2, "cz-b": 1}, 3) == "cz-a"


def test_pick_dominant_cloud_zone_returns_empty_when_no_zone_reaches_half():
    assert _pick_dominant_cloud_zone({"cz-a": 1, "cz-b": 1, "cz-c": 1}, 3) == ""


def test_pick_dominant_cloud_zone_ignores_empty_zone_and_zero_total():
    assert _pick_dominant_cloud_zone({"": 3}, 3) == ""
    assert _pick_dominant_cloud_zone({"cz-a": 1}, 0) == ""


def test_sub_zone_ids_of_cloud_zone_prefers_subzone_mapping():
    with patch.object(ticket_module.BKSubzone.objects, "filter") as filter_mock:
        filter_mock.return_value.values_list.return_value = [22, 21]

        assert _sub_zone_ids_of_cloud_zone("cz-a", {99}) == [21, 22]


def test_sub_zone_ids_of_cloud_zone_falls_back_to_machine_sub_zones():
    with patch.object(ticket_module.BKSubzone.objects, "filter") as filter_mock:
        filter_mock.return_value.values_list.return_value = []

        assert _sub_zone_ids_of_cloud_zone("cz-a", {99, 98}) == [98, 99]


def test_mongos_excludes_whole_cloud_zone_when_half_healthy_in_it():
    """3 台健康 mongos 里 2 台在 cz-a，应排除 cz-a 下的所有园区。"""
    healthy = [
        _machine("1.1.1.1", "cz-a", 11),
        _machine("1.1.1.2", "cz-a", 12),
        _machine("1.1.1.3", "cz-b", 21),
        _machine("1.1.1.4", "cz-b", 22),  # 故障机
    ]
    cluster = _cluster(healthy)

    with patch.object(ticket_module.Cluster.objects, "get", return_value=cluster), patch.object(
        ticket_module.BKSubzone.objects, "filter"
    ) as filter_mock:
        filter_mock.return_value.values_list.return_value = [11, 12]
        spec = mongos_get_resource_spec(cluster_id=1, mongos_list=[_host("1.1.1.4")])

    location_spec = spec["1.1.1.4"]["location_spec"]
    assert location_spec["include_or_exclue"] is False
    assert location_spec["sub_zone_ids"] == [11, 12]


def test_mongos_keeps_any_zone_when_healthy_spread_across_cloud_zones():
    healthy = [
        _machine("1.1.1.1", "cz-a", 11),
        _machine("1.1.1.2", "cz-b", 21),
        _machine("1.1.1.3", "cz-c", 31),
        _machine("1.1.1.4", "cz-b", 22),  # 故障机
    ]
    cluster = _cluster(healthy)

    with patch.object(ticket_module.Cluster.objects, "get", return_value=cluster), patch.object(
        ticket_module.BKSubzone.objects, "filter"
    ) as filter_mock:
        filter_mock.return_value.values_list.return_value = [11]
        spec = mongos_get_resource_spec(cluster_id=1, mongos_list=[_host("1.1.1.4")])

    location_spec = spec["1.1.1.4"]["location_spec"]
    assert location_spec["include_or_exclue"] is True
    assert location_spec["sub_zone_ids"] == []


def test_mongod_excludes_cloud_zone_by_machine_sub_zones_when_map_missing():
    healthy = [
        _machine("1.1.1.1", "cz-a", 11),
        _machine("1.1.1.2", "cz-a", 12),
        _machine("1.1.1.3", "cz-b", 21),
        _machine("1.1.1.4", "cz-b", 22),  # 故障机
    ]
    cluster = _cluster(healthy)

    with patch.object(ticket_module.Cluster.objects, "get", return_value=cluster), patch.object(
        ticket_module.BKSubzone.objects, "filter"
    ) as filter_mock:
        # BKSubzone 没同步到该可用区时，回落到机器实际所在园区
        filter_mock.return_value.values_list.return_value = []
        spec = mongod_get_resource_spec(cluster_id=1, mongod_list=[_host("1.1.1.4")])

    location_spec = spec["1.1.1.4"]["location_spec"]
    assert location_spec["include_or_exclue"] is False
    assert location_spec["sub_zone_ids"] == [11, 12]
