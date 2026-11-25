# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.flow.plugins.components.collections.mongodb.mongo_replace_probe_down import (
    decide_replace_alive,
    drs_ping_ok,
    explain_replace_decision,
    replace_down_flag,
    source_down_decision,
)


def _probe(dead_ips):
    def probe(ip, bk_cloud_id):
        if ip in dead_ips:
            return False
        if ip == "127.0.0.9":
            return None
        return True

    return probe


def test_replace_down_flag_matches_probe_node_output():
    hosts = [
        {"ip": "127.0.0.1", "bk_cloud_id": 0},
        {"ip": "127.0.0.2", "bk_cloud_id": 0, "down": True},
    ]
    assert replace_down_flag(hosts, _probe(set())) == 1
    assert replace_down_flag([{"ip": "127.0.0.3", "bk_cloud_id": 0}], _probe({"127.0.0.3"})) == 1
    assert replace_down_flag([{"ip": "127.0.0.9", "bk_cloud_id": 0}], _probe(set())) == 0
    assert replace_down_flag([{"ip": "127.0.0.5", "bk_cloud_id": 0}], _probe(set())) == 0


def test_uncertain_gse_with_dead_ports_is_down():
    """GSE 超时不能跳过端口检查。端口明确不可达时，死机不能再被当成活机。"""
    assert decide_replace_alive(None, False) is False
    assert decide_replace_alive(False, False) is False
    assert decide_replace_alive(False, True) is True
    assert decide_replace_alive(True, False) is True
    assert decide_replace_alive(None, None) is None
    assert decide_replace_alive(False, None) is None


def test_explain_replace_decision_covers_ambiguous_cases():
    down = explain_replace_decision(None, False)
    assert "decision=down" in down
    assert "gse=None" in down

    alive = explain_replace_decision(False, True)
    assert "decision=alive" in alive
    assert "ping.ok=1" in alive

    unknown = explain_replace_decision(False, None)
    assert "keep alive path" in unknown
    assert "cluster_id" in unknown
    assert explain_replace_decision(True, False) is None


def test_drs_error_text_is_not_reachable():
    """连接失败的回包不是异常，也不能当成 ping 成功。"""
    assert drs_ping_ok("1") is True
    assert drs_ping_ok("connect to server 127.0.0.1:27017\n1\ndisconnect.\n") is True
    assert drs_ping_ok("MongoNetworkError: connect ECONNREFUSED 127.0.0.1:27017") is False
    assert drs_ping_ok("0") is False
    assert drs_ping_ok(None) is False


def test_drs_exception_is_unknown_not_unreachable():
    """DRS 网关异常、鉴权失败等无法完成探测，不能当成端口不可达。"""
    from unittest.mock import patch

    from backend.flow.plugins.components.collections.mongodb.mongo_replace_probe_down import _mongo_port_reachable

    # 让 DRS 参数构建成功，走到 DRS 调用；DRS 抛异常应返回 None（未知），不是 False（不可达）
    with patch(
        "backend.flow.utils.mongodb.mongodb_util.MongoUtil.get_mongodb_DRS_args_direct",
        return_value={"fake": True},
    ), patch("backend.components.DRSApi.mongodb_rpc", side_effect=Exception("drs gateway error")):
        assert _mongo_port_reachable("127.0.0.1", 27017, 100, log_fn=None) is None


def test_source_down_needs_gse_and_data_plane():
    assert source_down_decision([False, False, False], False) is True
    assert source_down_decision([False], True) is False
    assert source_down_decision([False], None) is False
    assert source_down_decision([False, None], False) is False
    assert source_down_decision([True], False) is False
    assert source_down_decision([], False) is False


def test_mongos_change_meta_respects_host_down_flag():
    from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

    ak = ActKwargs()
    info = {
        "db_type": "mongos",
        "created_by": "admin",
        "bk_biz_id": 3,
        "mongos": [
            {
                "ip": "127.0.0.1",
                "down": True,
                "instances": [{"cluster_id": 9, "port": 27021}],
                "target": {"ip": "127.0.0.2", "spec": {"id": 1}},
            }
        ],
    }
    kwargs = ak.get_change_meta_replace_kwargs(info=info, instance={})
    assert kwargs["defer_deinstall"] is True


def test_old_host_instances_extracts_seg_range_for_cluster_role():
    from backend.flow.consts import MongoDBClusterRole
    from backend.flow.engine.bamboo.scene.mongodb.sub_task.replicaset_replace import _old_host_instances

    info = {
        "ip": "127.0.0.1",
        "bk_cloud_id": 0,
        "instances": [{"port": 27001, "seg_range": "shard-s1", "cluster_name": "cls"}],
    }
    old_hosts, old_instances = _old_host_instances(info, MongoDBClusterRole.ShardSvr.value)
    assert old_hosts == [{"ip": "127.0.0.1", "bk_cloud_id": 0}]
    assert old_instances == [{"ip": "127.0.0.1", "bk_cloud_id": 0, "port": 27001, "set_id": "shard-s1"}]
