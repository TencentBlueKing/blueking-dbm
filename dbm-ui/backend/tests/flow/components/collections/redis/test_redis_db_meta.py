# -*- coding: utf-8 -*-
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.db_meta.enums import ClusterType, MachineType
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta


class _DistinctValues(list):
    def distinct(self):
        return self


class _ClusterMonitorTopoQuery:
    def __init__(self, machine_types):
        self.machine_types = machine_types

    def values_list(self, *_args, **_kwargs):
        return _DistinctValues(self.machine_types)


class _EmptyMachineQuery:
    def values(self, *_args, **_kwargs):
        return []


def test_redis_install_prefers_activity_cluster_type_over_ticket_data():
    ticket_data = {
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "created_by": "admin",
        "cluster_type": ClusterType.TendisRedisInstance.value,
    }
    activity_cluster = {
        "bk_cloud_id": 0,
        "cluster_type": ClusterType.TendisPredixyTendisplusCluster.value,
        "new_master_ips": ["1.1.1.3"],
        "new_slave_ips": [],
        "inst_num": 1,
        "start_port": 30000,
        "spec_id": 1,
        "spec_config": {"cpu": 1},
    }

    with patch("backend.flow.utils.redis.redis_db_meta.atomic", return_value=nullcontext()), patch(
        "backend.flow.utils.redis.redis_db_meta.api.machine.create"
    ) as mock_machine_create, patch("backend.flow.utils.redis.redis_db_meta.api.storage_instance.create"):
        RedisDBMeta(ticket_data=ticket_data, cluster=activity_cluster).redis_install()

    machines = mock_machine_create.call_args.kwargs["machines"]
    assert machines[0]["machine_type"] == MachineType.TENDISPLUS.value


def test_redis_install_append_prefers_activity_cluster_type_over_ticket_data():
    ticket_data = {
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "created_by": "admin",
        "cluster_type": ClusterType.TendisRedisInstance.value,
    }
    activity_cluster = {
        "bk_cloud_id": 0,
        "cluster_type": ClusterType.TendisPredixyTendisplusCluster.value,
        "master_ip": "1.1.1.3",
        "slave_ip": "1.1.1.4",
        "ports": [30000],
        "spec_id": 1,
        "spec_config": {"cpu": 1},
    }

    with patch("backend.flow.utils.redis.redis_db_meta.atomic", return_value=nullcontext()), patch(
        "backend.flow.utils.redis.redis_db_meta.Machine.objects.filter", return_value=_EmptyMachineQuery()
    ), patch("backend.flow.utils.redis.redis_db_meta.api.machine.create") as mock_machine_create, patch(
        "backend.flow.utils.redis.redis_db_meta.api.storage_instance.create"
    ):
        RedisDBMeta(ticket_data=ticket_data, cluster=activity_cluster).redis_install_append()

    machine_types = {machine["machine_type"] for machine in mock_machine_create.call_args.kwargs["machines"]}
    assert machine_types == {MachineType.TENDISPLUS.value}


def test_redis_rollback_host_transfer_rejects_missing_cluster_module_before_calling_cc():
    ticket_data = {"bk_biz_id": 3, "created_by": "admin"}
    activity_cluster = {
        "bk_cloud_id": 0,
        "immute_domain": "plus.test.dba.db",
        "tendiss": [{"receiver": {"ip": "1.1.1.3", "port": 30000}}],
    }
    temp_instance = SimpleNamespace(
        machine=SimpleNamespace(ip="1.1.1.3", bk_host_id=123),
        port=30000,
        machine_type=MachineType.TENDISCACHE.value,
    )
    source_cluster = SimpleNamespace(id=101, immute_domain="plus.test.dba.db")

    with patch("backend.flow.utils.redis.redis_db_meta.atomic", return_value=nullcontext()), patch(
        "backend.flow.utils.redis.redis_db_meta.StorageInstance.objects.get", return_value=temp_instance
    ), patch("backend.flow.utils.redis.redis_db_meta.Cluster.objects.get", return_value=source_cluster), patch(
        "backend.flow.utils.redis.redis_db_meta.ClusterMonitorTopo.objects.filter",
        return_value=_ClusterMonitorTopoQuery([MachineType.PREDIXY.value, MachineType.TENDISPLUS.value]),
    ), patch(
        "backend.flow.utils.redis.redis_db_meta.RedisCCTopoOperator"
    ) as mock_cc_operator:
        with pytest.raises(Exception) as exc_info:
            RedisDBMeta(ticket_data=ticket_data, cluster=activity_cluster).redis_rollback_host_transfer()

    error_message = str(exc_info.value)
    assert "cluster_id=101" in error_message
    assert "domain=plus.test.dba.db" in error_message
    assert "1.1.1.3:30000" in error_message
    assert MachineType.TENDISCACHE.value in error_message
    assert MachineType.TENDISPLUS.value in error_message
    mock_cc_operator.assert_not_called()
