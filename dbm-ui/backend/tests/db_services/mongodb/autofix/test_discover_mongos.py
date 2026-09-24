# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import patch

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_services.mongodb.autofix.discover_mongos import (
    apply_mongos_mongo_ignore,
    host_switch_all_success,
    is_mongos_switch_host,
    next_mongos_dbha_cursor,
)
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import is_mongos_core
from backend.db_services.mongodb.autofix.ticket_create import create_autofix_pre_ticket
from backend.ticket.constants import TicketType


def _host(**kwargs):
    data = {
        "bk_biz_id": 3,
        "cluster_id": 1,
        "cluster_type": ClusterType.MongoShardedCluster.value,
        "immute_domain": "mongo.example.db",
        "instance_type": MachineType.MONGOS.value,
        "cluster_ports": [27017],
        "bk_host_id": 11,
        "ip": "127.0.0.1",
        "switch_ports": [27017],
        "sw_min_id": 10,
        "sw_max_id": 10,
        "sw_result": {"success": [27017]},
        "ignore_fix": False,
    }
    data.update(kwargs)
    return SimpleNamespace(**data)


def test_is_mongos_switch_host():
    assert is_mongos_switch_host(_host()) is True
    assert is_mongos_switch_host(_host(cluster_type="TwemproxyRedisInstance")) is False
    assert is_mongos_switch_host(_host(instance_type="mongodb")) is False


def test_host_switch_all_success():
    assert host_switch_all_success(_host()) is True
    assert host_switch_all_success(_host(switch_ports=[], sw_result={})) is False


def test_next_cursor_skips_non_mongos_and_waits_incomplete_mongos():
    queues = [{"uid": 5}, {"uid": 8}]
    waiting = _host(sw_min_id=6, switch_ports=[], sw_result={})
    assert next_mongos_dbha_cursor(1, queues, [waiting]) == 6
    done = _host()
    assert next_mongos_dbha_cursor(1, queues, [done]) == 9
    assert next_mongos_dbha_cursor(3, [], []) == 3


def test_apply_mongos_mongo_ignore_whitelist():
    host = _host()
    with patch(
        "backend.db_services.mongodb.autofix.discover_mongos.ctl.is_whitelist_allowed",
        return_value=False,
    ), patch(
        "backend.db_services.mongodb.autofix.discover_mongos._record_ignore",
    ) as record:
        assert apply_mongos_mongo_ignore([host]) == []
    assert record.call_args.kwargs["ignore_msg"] == "not_in_whitelist"


def test_is_mongos_core():
    core = SimpleNamespace(fault_machines=[{"machine_type": "mongos"}], roles=["mongos"])
    assert is_mongos_core(core) is True
    mongod = SimpleNamespace(fault_machines=[{"machine_type": "mongodb"}], roles=["m1"])
    assert is_mongos_core(mongod) is False


def test_create_autofix_pre_ticket_marks_mongos_wait_forever():
    core = SimpleNamespace(
        id=9,
        ip="127.0.0.1",
        bk_host_id=11,
        bk_cloud_id=0,
        bk_biz_id=3,
        cluster_ids=[1],
        cluster_id=1,
        ports=[27017],
        cluster_type=ClusterType.MongoShardedCluster.value,
        immute_domain="mongo.example.db",
        fault_machines=[{"machine_type": "mongos"}],
        roles=["mongos"],
    )
    created = SimpleNamespace(id=88)
    with (
        patch(
            "backend.db_services.mongodb.autofix.ticket_create._mongodb_dba",
            return_value="admin",
        ),
        patch(
            "backend.db_services.mongodb.autofix.ticket_create.Ticket.create_ticket",
            return_value=created,
        ) as create_ticket,
        patch("backend.db_services.mongodb.autofix.ticket_create.notify.send_msg.apply_async"),
        patch("backend.db_services.mongodb.autofix.ticket_create.write_autofix_log"),
    ):
        ticket = create_autofix_pre_ticket(core)

    assert ticket is created
    info = create_ticket.call_args.kwargs["details"]["infos"][0]
    assert create_ticket.call_args.kwargs["ticket_type"] == TicketType.MONGODB_AUTOFIX_PRE.value
    assert info["wait_gse_forever"] is True
    assert info["machine_type"] == MachineType.MONGOS.value
