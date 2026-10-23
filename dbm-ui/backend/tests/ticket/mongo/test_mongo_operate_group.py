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
from backend.db_services.mongodb.autofix.mongodb_autofix_ticket import collect_mongo_groups
from backend.ticket.mongo_operate_group import mongo_groups_allow_parallel


def test_mongo_groups_allow_parallel_only_when_both_sides_disjoint():
    assert mongo_groups_allow_parallel(["shard:1:s1"], ["shard:1:s2"]) is True
    assert mongo_groups_allow_parallel(["mongos:1"], ["shard:1:s1"]) is True
    assert mongo_groups_allow_parallel(["shard:1:s1"], ["shard:1:s1"]) is False
    assert mongo_groups_allow_parallel(["shard:1:s1", "mongos:1"], ["mongos:1"]) is False
    assert mongo_groups_allow_parallel([], ["shard:1:s1"]) is False
    assert mongo_groups_allow_parallel(["shard:1:s1"], None) is False
    assert mongo_groups_allow_parallel(None, None) is False


def test_collect_mongo_groups_sorts_unique_affinity():
    mongos = [{"ip": "127.0.0.1", "affinity_group": "mongos:8"}]
    mongod = [
        {"ip": "127.0.0.2", "affinity_group": "shard:8:s2"},
        {"ip": "127.0.0.3", "affinity_group": "shard:8:s1"},
        {"ip": "127.0.0.4"},
    ]
    assert collect_mongo_groups(mongos, mongod) == ["mongos:8", "shard:8:s1", "shard:8:s2"]
    assert collect_mongo_groups([], None) == []
