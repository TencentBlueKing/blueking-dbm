# -*- coding: utf-8 -*-
import importlib
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def mysql_affinity_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(
            "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.mysql_cluster_check.check_affinity"
        )


def _instance(ip: str, cloud_zone: str, rack_id: int, subzone_id: int, city_id: int = 1):
    return SimpleNamespace(
        machine=SimpleNamespace(
            ip=ip,
            bk_cloud_zone=cloud_zone,
            bk_sub_zone_id=subzone_id,
            bk_rack_id=rack_id,
            bk_sub_zone=f"subzone-{subzone_id}",
            bk_rack=f"rack-{rack_id}",
            bk_city=SimpleNamespace(bk_idc_city_id=city_id, bk_idc_city_name="shenzhen"),
        )
    )


def test_cross_cloud_zone_violates_when_same_cloud_zone_but_different_subzones(mysql_affinity_module):
    """同一可用区、不同园区不再视为已分散：CROS_SUBZONE 应判定违规。"""
    checker = mysql_affinity_module.MySQLAffinityChecker

    msg = checker._check_backend_cross_cloud_zone(
        _instance("1.1.1.1", "cz-a", 11, subzone_id=1),
        _instance("1.1.1.2", "cz-a", 12, subzone_id=2),
        expected_city_ids=set(),
    )

    assert msg is not None
    assert "在同一可用区" in msg


def test_cross_cloud_zone_passes_when_different_cloud_zones(mysql_affinity_module):
    checker = mysql_affinity_module.MySQLAffinityChecker

    msg = checker._check_backend_cross_cloud_zone(
        _instance("1.1.1.1", "cz-a", 11, subzone_id=1),
        _instance("1.1.1.2", "cz-b", 11, subzone_id=2),
        expected_city_ids=set(),
    )

    assert msg is None


def test_same_cloud_zone_cross_rack_still_requires_different_racks(mysql_affinity_module):
    """机架判断不变：同可用区同机架仍然违规。"""
    checker = mysql_affinity_module.MySQLAffinityChecker

    msg = checker._check_backend_same_cloud_zone(
        _instance("1.1.1.1", "cz-a", 11, subzone_id=1),
        _instance("1.1.1.2", "cz-a", 11, subzone_id=2),
    )

    assert msg is not None
    assert "在同一机架" in msg


def test_same_cloud_zone_cross_rack_passes_with_different_racks(mysql_affinity_module):
    checker = mysql_affinity_module.MySQLAffinityChecker

    msg = checker._check_backend_same_cloud_zone(
        _instance("1.1.1.1", "cz-a", 11, subzone_id=1),
        _instance("1.1.1.2", "cz-a", 12, subzone_id=2),
    )

    assert msg is None


def test_proxies_same_cloud_zone_across_subzones_counts_as_single_zone(mysql_affinity_module):
    """同一可用区下不同园区的 proxy 视为同区，不再因园区不同判违规。"""
    checker = mysql_affinity_module.MySQLAffinityChecker
    proxies = [
        _instance("1.1.1.1", "cz-a", 11, subzone_id=1),
        _instance("1.1.1.2", "cz-a", 12, subzone_id=2),
    ]

    result = checker._validate_proxies_affinity(
        proxy_instances=proxies,
        affinity_level=mysql_affinity_module.AffinityEnum.SAME_SUBZONE_CROSS_SWTICH.value,
        expected_city_ids=set(),
    )

    assert result["state"] == mysql_affinity_module.ReportStateType.NORMAL.value
    assert result["msg"] == ""


def test_proxies_cross_cloud_zone_violates_when_single_cloud_zone(mysql_affinity_module):
    checker = mysql_affinity_module.MySQLAffinityChecker
    proxies = [
        _instance("1.1.1.1", "cz-a", 11, subzone_id=1),
        _instance("1.1.1.2", "cz-a", 12, subzone_id=2),
    ]

    result = checker._validate_proxies_affinity(
        proxy_instances=proxies,
        affinity_level=mysql_affinity_module.AffinityEnum.CROS_SUBZONE.value,
        expected_city_ids=set(),
    )

    # 2 个 proxy 全部落在一个可用区，超过 ceil(2*0.5)=1 的上限
    assert result["state"] == mysql_affinity_module.ReportStateType.ABNORMAL.value
    assert "在可用区 cz-a 中超过限制" in result["msg"]


def test_format_machine_info_uses_cloud_zone(mysql_affinity_module):
    checker = mysql_affinity_module.MySQLAffinityChecker

    info = checker._format_machine_info(_instance("1.1.1.1", "cz-a", 11, subzone_id=3).machine)

    assert "cz-a" in info
    assert "可用区" in info
