# -*- coding: utf-8 -*-
import json
from unittest.mock import MagicMock, patch

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.autofix.bill import generate_single_autofix_ticket
from backend.db_services.redis.autofix.enums import AutofixStatus


def _cluster(instance_type):
    cluster = MagicMock()
    cluster.fault_machines = json.dumps([{"ip": "127.0.0.1", "instance_type": instance_type}])
    cluster.cluster_id = 1
    cluster.bk_biz_id = 3
    cluster.cluster_type = ClusterType.MongoReplicaSet.value
    cluster.immute_domain = "m1.example.db"
    return cluster


def _machine():
    machine = MagicMock()
    machine.spec_id = 1
    machine.bk_sub_zone = "z"
    machine.bk_sub_zone_id = 1
    machine.bk_city.logical_city.name = "sz"
    machine.spec_config = {}
    machine.bk_host_id = 9
    return machine


def test_mongod_keeps_redis_ticket_when_mongo_autofix_off():
    cluster = _cluster("m1")
    with patch("backend.db_services.redis.autofix.bill.mongodb_autofix_enabled", return_value=False,), patch(
        "backend.db_services.redis.autofix.bill.Machine"
    ) as machine_cls, patch(
        "backend.db_services.redis.autofix.bill.query_cluster_by_hosts",
        return_value=[{"cluster_id": 1, "cluster": "m1.example.db"}],
    ), patch(
        "backend.db_services.redis.autofix.bill.mongo_create_ticket"
    ) as create:
        machine_cls.objects.filter.return_value.get.return_value = _machine()
        generate_single_autofix_ticket(cluster)
    create.assert_called_once()
    assert create.call_args.args[2] == []
    assert create.call_args.args[3][0]["ip"] == "127.0.0.1"
    cluster.save.assert_not_called()


def test_mongod_ignored_when_mongo_autofix_on():
    cluster = _cluster("m1")
    with patch(
        "backend.db_services.redis.autofix.bill.mongodb_autofix_enabled",
        return_value=True,
    ), patch("backend.db_services.redis.autofix.bill.mongo_create_ticket") as create:
        generate_single_autofix_ticket(cluster)
    create.assert_not_called()
    assert cluster.deal_status == AutofixStatus.AF_IGNORE.value
    assert cluster.status_version != "mongo_handled_by_mongodb_autofix"
    cluster.save.assert_called_once()
