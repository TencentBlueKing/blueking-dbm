# -*- coding: utf-8 -*-
import importlib
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def redis_affinity_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(
            "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.redis_cluster_check.check_affinity"
        )


def _storage(ip: str, subzone_id: int, rack_id: str):
    return SimpleNamespace(machine=SimpleNamespace(ip=ip, bk_sub_zone_id=subzone_id, bk_rack_id=rack_id))


def test_same_subzone_cross_switch_suggests_moving_slave_to_expected_subzone(redis_affinity_module):
    checker = redis_affinity_module.RedisAffinityChecker
    checker._subzone_map_cache = {1: "test-subzone-a", 2: "test-subzone-b"}

    msg = checker._check_backend_same_subzone(
        master_obj=_storage("1.1.1.1", 1, "rack-a"),
        slave_obj=_storage("1.1.1.2", 2, "rack-b"),
        expected_subzone_id=1,
    )

    assert "请将副节点机器 1.1.1.2 替换或迁移到 园区(test-subzone-a) 且不同机架" in msg
    assert "主节点机器 1.1.1.1 替换" not in msg


def test_same_subzone_cross_switch_suggests_moving_master_when_slave_is_in_expected_subzone(redis_affinity_module):
    checker = redis_affinity_module.RedisAffinityChecker
    checker._subzone_map_cache = {1: "test-subzone-a", 2: "test-subzone-b"}

    msg = checker._check_backend_same_subzone(
        master_obj=_storage("1.1.1.2", 2, "rack-b"),
        slave_obj=_storage("1.1.1.1", 1, "rack-a"),
        expected_subzone_id=1,
    )

    assert "请将主节点机器 1.1.1.2 替换或迁移到 园区(test-subzone-a) 且不同机架" in msg
    assert "副节点机器 1.1.1.1 替换" not in msg
