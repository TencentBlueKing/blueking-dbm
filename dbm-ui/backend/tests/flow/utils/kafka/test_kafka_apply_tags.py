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
# 校验 Kafka 部署单据的 tags 链路：flow 层把 tags 透传给 api.cluster.kafka.create，
# 建集群元数据时用真实的 Cluster.id 绑定标签；没有 tags 时保持原有行为。纯 mock，不依赖数据库。
from contextlib import ExitStack, nullcontext
from unittest import mock

import pytest

from backend.db_meta.api.cluster.kafka.create import create as kafka_cluster_create
from backend.flow.utils.kafka.kafka_db_meta import KafkaMeta

_FLOW_MODULE = "backend.flow.utils.kafka.kafka_db_meta"
_API_MODULE = "backend.db_meta.api.cluster.kafka.create"

# 区分「调用方没传 tags」和「显式传了 tags=None」两种情况
_UNSET = object()


def _ticket_data(**extra) -> dict:
    data = {
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "created_by": "admin",
        "cluster_name": "kafka01",
        "cluster_alias": "kafka01",
        "domain": "kafka.kafka01.demo.db",
        "db_version": "3.6.0",
        "city_code": "sz",
        "disaster_tolerance_level": "NONE",
        "ip_source": "manual_input",
        "port": 9092,
        "nodes": {
            "broker": [{"ip": "127.0.0.1", "bk_cloud_id": 0}],
            "zookeeper": [{"ip": "127.0.0.2", "bk_cloud_id": 0}],
        },
    }
    data.update(extra)
    return data


@pytest.fixture
def patched_flow():
    new_cluster = mock.MagicMock(id=1001, bk_biz_id=3)
    new_cluster.storageinstance_set.filter.return_value = []
    with mock.patch(f"{_FLOW_MODULE}.atomic", return_value=nullcontext()), mock.patch(
        f"{_FLOW_MODULE}.api"
    ) as api, mock.patch(f"{_FLOW_MODULE}.KafkaCCTopoOperator"):
        api.cluster.kafka.create.return_value = new_cluster
        yield api.cluster.kafka.create


def test_kafka_apply_forwards_tags_to_cluster_create(patched_flow):
    tags = [{"env": "test"}, {"team": "db"}]

    assert KafkaMeta(_ticket_data(tags=tags)).kafka_apply() is True

    patched_flow.assert_called_once()
    assert patched_flow.call_args.kwargs["tags"] == tags


def test_kafka_apply_without_tags_forwards_empty_list(patched_flow):
    assert KafkaMeta(_ticket_data()).kafka_apply() is True

    patched_flow.assert_called_once()
    assert patched_flow.call_args.kwargs["tags"] == []


@pytest.fixture
def patched_create():
    cluster_obj = mock.MagicMock(id=1001)
    names = ("request_validator", "common", "Cluster", "ClusterEntry", "StorageInstance", "add_cluster_tag_keys")
    with ExitStack() as stack:
        patched = {name: stack.enter_context(mock.patch(f"{_API_MODULE}.{name}")) for name in names}
        validator = patched["request_validator"]
        validator.validated_integer.side_effect = lambda value: value
        validator.validated_domain.side_effect = lambda value: value
        validator.validated_storage_list.side_effect = lambda value, **kwargs: value
        patched["Cluster"].objects.create.return_value = cluster_obj
        yield patched["add_cluster_tag_keys"], patched["Cluster"]


def _call_create(tags=_UNSET, **overrides):
    kwargs = {
        "bk_cloud_id": 0,
        "bk_biz_id": 3,
        "name": "kafka01",
        "alias": "kafka01",
        "immute_domain": "kafka.kafka01.demo.db",
        "db_module_id": 123,
        "db_version": "3.6.0",
    }
    kwargs.update(overrides)
    if tags is not _UNSET:
        kwargs["tags"] = tags
    # create 被 @transaction.atomic 包装，单测里直接调用未包装的实现，避免连库
    return kafka_cluster_create.__wrapped__(**kwargs)


def test_create_binds_tags_with_real_cluster_id(patched_create):
    add_tags, _ = patched_create
    tags = [{"env": "test"}, {"team": "db"}]

    _call_create(tags=tags)

    add_tags.assert_called_once_with(bk_biz_id=3, cluster_ids=[1001], tags=tags)


@pytest.mark.parametrize("tags", [_UNSET, None, []], ids=["omitted", "explicit_none", "empty_list"])
def test_create_without_tags_binds_empty_list(patched_create, tags):
    add_tags, _ = patched_create

    _call_create(tags=tags)

    add_tags.assert_called_once_with(bk_biz_id=3, cluster_ids=[1001], tags=[])


def test_create_binds_tags_right_after_cluster_created(patched_create):
    add_tags, cluster_model = patched_create
    calls = []
    cluster_model.objects.create.side_effect = lambda **kwargs: calls.append("create") or mock.MagicMock(id=1001)
    add_tags.side_effect = lambda **kwargs: calls.append("bind")

    _call_create(tags=[{"env": "test"}])

    assert calls == ["create", "bind"]
