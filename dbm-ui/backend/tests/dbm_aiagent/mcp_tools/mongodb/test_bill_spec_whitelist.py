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
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.exceptions import ValidationError

from backend.dbm_aiagent.mcp_tools.mongodb.impl import mongodb_bill as bill_impl
from backend.dbm_aiagent.mcp_tools.mongodb.serializers.mongodb_bill import (
    SubmitBillMongoReplicaSetApplyInputSerializer,
    SubmitBillMongoShardApplyInputSerializer,
)

_WHITELIST_PATH = "backend.dbm_aiagent.mcp_tools.mongodb.serializers.mongodb_bill.filter_disallowed_spec_ids"


def _replicaset_payload(**overrides):
    payload = {
        "bk_biz_id": 3,
        "db_app_abbr": "dba",
        "db_version": "mongodb-6.0.27",
        "spec_id": 11,
        "replica_count": 2,
        "node_count": 3,
        "node_replica_count": 1,
        "replica_sets": [
            {"set_id": "rs0", "domain": "m1.rs0.dba.db"},
            {"set_id": "rs1", "domain": "m1.rs1.dba.db"},
        ],
    }
    payload.update(overrides)
    return payload


def _shard_payload(**overrides):
    payload = {
        "bk_biz_id": 3,
        "db_app_abbr": "dba",
        "cluster_name": "shard0",
        "db_version": "mongodb-6.0.27",
        "shard_num": 2,
        "shard_machine_group": 2,
        "resource_spec": {
            "mongodb": {"spec_id": 11, "count": 6},
            "mongo_config": {"spec_id": 12, "count": 3},
            "mongos": {"spec_id": 13, "count": 2},
        },
    }
    payload.update(overrides)
    return payload


class TestReplicaSetSpecWhitelist:
    def test_allowed_spec_pass(self):
        with patch(_WHITELIST_PATH, return_value=[]) as mocked:
            slz = SubmitBillMongoReplicaSetApplyInputSerializer(data=_replicaset_payload())
            slz.is_valid(raise_exception=True)
            assert 11 in mocked.call_args[0][0]

    def test_disallowed_spec_rejected(self):
        with patch(_WHITELIST_PATH, return_value=[99]):
            slz = SubmitBillMongoReplicaSetApplyInputSerializer(data=_replicaset_payload(spec_id=99))
            with pytest.raises(ValidationError):
                slz.is_valid(raise_exception=True)

    def test_resource_spec_ids_also_checked(self):
        """resource_spec 里夹带的 spec_id 同样要过白名单"""
        with patch(_WHITELIST_PATH, return_value=[]) as mocked:
            payload = _replicaset_payload(resource_spec={"mongo_machine_set": {"spec_id": 77, "count": 3}})
            slz = SubmitBillMongoReplicaSetApplyInputSerializer(data=payload)
            slz.is_valid(raise_exception=True)
            assert set(mocked.call_args[0][0]) == {11, 77}

    @pytest.mark.parametrize("node_count", [1, 2, 4])
    def test_only_three_node_replicaset_allowed(self, node_count):
        with patch(_WHITELIST_PATH, return_value=[]):
            slz = SubmitBillMongoReplicaSetApplyInputSerializer(data=_replicaset_payload(node_count=node_count))
            with pytest.raises(ValidationError, match="3 节点副本集"):
                slz.is_valid(raise_exception=True)


class TestShardSpecWhitelist:
    def test_allowed_spec_pass(self):
        with patch(_WHITELIST_PATH, return_value=[]) as mocked:
            slz = SubmitBillMongoShardApplyInputSerializer(data=_shard_payload())
            slz.is_valid(raise_exception=True)
            assert set(mocked.call_args[0][0]) == {11, 12, 13}

    def test_disallowed_spec_rejected(self):
        with patch(_WHITELIST_PATH, return_value=[13]):
            slz = SubmitBillMongoShardApplyInputSerializer(data=_shard_payload())
            with pytest.raises(ValidationError):
                slz.is_valid(raise_exception=True)

    def test_missing_spec_id_rejected(self):
        """缺 spec_id 不能绕过白名单校验"""
        resource_spec = {
            "mongodb": {"count": 6},
            "mongo_config": {"spec_id": 12, "count": 3},
            "mongos": {"spec_id": 13, "count": 2},
        }
        with patch(_WHITELIST_PATH, return_value=[]):
            slz = SubmitBillMongoShardApplyInputSerializer(data=_shard_payload(resource_spec=resource_spec))
            with pytest.raises(ValidationError):
                slz.is_valid(raise_exception=True)

    @pytest.mark.parametrize(
        "role,count,error",
        [
            ("mongodb", 2, "3 节点 shardsvr"),
            ("mongodb", 8, "3 节点 shardsvr"),
            ("mongo_config", 1, "3 节点 configsvr"),
            ("mongos", 1, "mongos count 不能少于 2"),
        ],
    )
    def test_only_standard_shard_topology_allowed(self, role, count, error):
        resource_spec = _shard_payload()["resource_spec"]
        resource_spec[role] = {**resource_spec[role], "count": count}
        with patch(_WHITELIST_PATH, return_value=[]):
            slz = SubmitBillMongoShardApplyInputSerializer(data=_shard_payload(resource_spec=resource_spec))
            with pytest.raises(ValidationError, match=error):
                slz.is_valid(raise_exception=True)


class TestFilterDisallowedSpecIds:
    def test_returns_ids_outside_whitelist(self):
        queryset = MagicMock()
        queryset.filter.return_value.values_list.return_value = [11, 12]
        with patch.object(bill_impl, "_mcp_allowed_spec_queryset", return_value=queryset):
            assert bill_impl.filter_disallowed_spec_ids([11, 12, 99]) == [99]

    def test_empty_input_skips_query(self):
        with patch.object(bill_impl, "_mcp_allowed_spec_queryset") as mocked:
            assert bill_impl.filter_disallowed_spec_ids([None]) == []
            mocked.assert_not_called()
