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
from backend.flow.engine.bamboo.scene.mongodb.mongodb_machine_replace import apply_down_if_unreachable
from backend.flow.plugins.components.collections.mongodb.mongo_replace_probe_down import replace_down_flag


def _probe(dead_ips):
    def probe(ip, bk_cloud_id):
        if ip in dead_ips:
            return False
        if ip == "127.0.0.9":
            return None
        return True

    return probe


def test_apply_down_marks_only_explicit_gse_failure():
    data = {
        "cluster_type": "MongoShardedCluster",
        "infos": [
            {
                "cluster_id": 1,
                "mongodb": [{"ip": "127.0.0.1", "bk_cloud_id": 0, "down": False}],
                "mongo_config": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
                "mongos": [{"ip": "127.0.0.3", "bk_cloud_id": 0, "down": True}],
            }
        ],
    }
    marked = apply_down_if_unreachable(data, _probe({"127.0.0.1"}))
    hosts = data["infos"][0]
    assert marked == ["127.0.0.1"]
    assert hosts["mongodb"][0]["down"] is True
    assert hosts["mongo_config"][0].get("down") is not True
    assert hosts["mongos"][0]["down"] is True


def test_apply_down_leaves_host_when_probe_uncertain():
    data = {
        "cluster_type": "MongoReplicaSet",
        "infos": [{"mongodb": [{"ip": "127.0.0.9", "bk_cloud_id": 0}]}],
    }
    assert apply_down_if_unreachable(data, _probe(set())) == []
    assert "down" not in data["infos"][0]["mongodb"][0]


def test_replace_down_flag_matches_probe_node_output():
    hosts = [
        {"ip": "127.0.0.1", "bk_cloud_id": 0},
        {"ip": "127.0.0.2", "bk_cloud_id": 0, "down": True},
    ]
    assert replace_down_flag(hosts, _probe(set())) == 1
    assert replace_down_flag([{"ip": "127.0.0.3", "bk_cloud_id": 0}], _probe({"127.0.0.3"})) == 1
    assert replace_down_flag([{"ip": "127.0.0.9", "bk_cloud_id": 0}], _probe(set())) == 0
    assert replace_down_flag([{"ip": "127.0.0.5", "bk_cloud_id": 0}], _probe(set())) == 0


def test_apply_down_replicaset_host_nested_under_mongodb():
    data = {
        "cluster_type": "MongoReplicaSet",
        "infos": [{"cluster_id": 2, "mongodb": [{"ip": "127.0.0.4", "bk_cloud_id": 0}]}],
    }
    assert apply_down_if_unreachable(data, _probe({"127.0.0.4"})) == ["127.0.0.4"]
    assert data["infos"][0]["mongodb"][0]["down"] is True
