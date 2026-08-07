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
import json

from backend.dbm_aiagent.mcp_tools.mongodb.impl.response_format import format_slowlog_list

_FULL_META = {
    "app": "bk-ci-devops",
    "appid": 100925,
    "cluster_domain": "bkrepoprodP.s2.devops.db",
    "cluster_name": "devops-s2-bkrepoprod",
    "cluster_role": "replicaset",
    "cluster_type": "MongoReplicaSet",
    "instance_set_name": "devops-s2-bkrepoprod",
    "instance": "127.0.0.1:27000",
    "instance_host": "127.0.0.1",
    "instance_port": 27000,
    "instance_role": "m2",
}

_SLIM_META = {
    "cluster_domain": "bkrepoprodP.s2.devops.db",
    "cluster_type": "MongoReplicaSet",
    "instance_set_name": "devops-s2-bkrepoprod",
    "instance": "127.0.0.1:27000",
    "instance_role": "m2",
}


def test_format_slowlog_list_parses_log_json_and_slims_meta():
    log_obj = {
        "meta": _FULL_META,
        "msg": "Slow query",
        "attr": {"ns": "bkrepo_prod.node_188", "durationMillis": "1106986"},
    }
    out = format_slowlog_list({"slowlog_entries": [{"log": json.dumps(log_obj)}]})
    assert out["total"] == 1
    item = out["items"][0]
    assert isinstance(item, dict)
    assert item["meta"] == _SLIM_META
    assert item["attr"]["ns"] == "bkrepo_prod.node_188"
    assert item["msg"] == "Slow query"


def test_format_slowlog_list_keeps_raw_string_when_parse_fails():
    raw = "not a json slowlog line"
    out = format_slowlog_list({"slowlog_entries": [{"log": raw}, {"log": "{bad"}]})
    assert out["total"] == 2
    assert out["items"] == [raw, "{bad"]


def test_format_slowlog_list_es_hits_source_log():
    """BKLog esquery hits._source.log 路径同样 parse + slim"""
    log_obj = {"meta": _FULL_META, "attr": {"queryHash": "F9BA5F6E"}}
    raw = {
        "slowlog_entries": {
            "hits": {
                "hits": [
                    {"_source": {"log": json.dumps(log_obj)}},
                    {"_source": {"log": "plain"}},
                ]
            }
        }
    }
    out = format_slowlog_list(raw)
    assert out["total"] == 2
    assert out["items"][0]["meta"] == _SLIM_META
    assert out["items"][1] == "plain"
