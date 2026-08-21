# -*- coding: utf-8 -*-
import importlib
from types import SimpleNamespace

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_report.enums import MetaCheckSubType


@pytest.fixture(scope="module")
def redis_instance_check_module(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        return importlib.import_module(
            "backend.db_periodic_task.local_tasks.db_meta.db_meta_check.redis_cluster_check.check_instance"
        )


def _enum_value(value):
    return str(getattr(value, "value", value))


def _machine(ip: str, machine_type: str = "tendiscache"):
    return SimpleNamespace(ip=ip, machine_type=machine_type)


def _storage(*, ip: str, port: int, role: str, status=InstanceStatus.RUNNING):
    inst = SimpleNamespace(
        instance_role=role,
        status=status,
        machine=_machine(ip),
        port=port,
        machine_type="tendiscache",
        ip_port=f"{ip}:{port}",
        as_ejector=SimpleNamespace(all=lambda: []),
        as_receiver=SimpleNamespace(all=lambda: []),
    )
    return inst


def _proxy(*, ip: str, port: int = 50000, status=InstanceStatus.RUNNING):
    return SimpleNamespace(
        status=status,
        machine=_machine(ip, "twemproxy"),
        port=port,
        machine_type="twemproxy",
        ip_port=f"{ip}:{port}",
    )


def _link_master_slave(master, slave):
    master.as_ejector = SimpleNamespace(all=lambda: [SimpleNamespace(receiver=slave)])
    slave.as_receiver = SimpleNamespace(all=lambda: [SimpleNamespace(ejector=master)])


def _cluster(*, cluster_type: str, proxies, storages, domain="a.redis.db"):
    return SimpleNamespace(
        cluster_type=cluster_type,
        immute_domain=domain,
        bk_biz_id=1001,
        proxyinstance_set=SimpleNamespace(all=lambda: list(proxies)),
        storageinstance_set=SimpleNamespace(all=lambda: list(storages)),
        tags=SimpleNamespace(all=lambda: []),
    )


def _healthy_redis_instance():
    master = _storage(ip="1.1.1.1", port=30000, role=InstanceRole.REDIS_MASTER.value)
    slave = _storage(ip="1.1.1.9", port=30000, role=InstanceRole.REDIS_SLAVE.value)
    _link_master_slave(master, slave)
    return _cluster(
        cluster_type=ClusterType.TendisRedisInstance.value,
        proxies=[],
        storages=[master, slave],
        domain="ok.redis.db",
    )


def _broken_twemproxy_cluster():
    master = _storage(
        ip="1.1.1.1",
        port=30000,
        role=InstanceRole.REDIS_MASTER.value,
        status=InstanceStatus.UNAVAILABLE,
    )
    return _cluster(
        cluster_type=ClusterType.TendisTwemproxyRedisInstance.value,
        proxies=[_proxy(ip="2.2.2.2", status=InstanceStatus.UNAVAILABLE)],
        storages=[master],
        domain="bad.redis.db",
    )


def test_instance_check_emitted_subtypes_are_mapped(redis_instance_check_module):
    """本检查发出的 subtype 必须 ⊆ INSTANCE_CHECK_PREFIX_BY_SUBTYPE，避免正常行被 ingest 丢成巡检缺口。"""
    mod = redis_instance_check_module
    rows = []
    rows.extend(mod._check_single_cluster_instance(_healthy_redis_instance(), "admin"))
    rows.extend(mod._check_single_cluster_instance(_broken_twemproxy_cluster(), "admin"))

    emitted = {_enum_value(row["subtype"]) for row in rows}
    mapped = set(mod.INSTANCE_CHECK_PREFIX_BY_SUBTYPE)
    assert emitted
    assert emitted <= mapped
    assert mapped == {
        MetaCheckSubType.AloneInstance.value,
        MetaCheckSubType.StatusAbnormal.value,
    }
