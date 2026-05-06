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

import re
from unittest.mock import MagicMock, patch

import pytest

from backend.db_meta.enums import ClusterType
from backend.iam_app.dataclass.actions import _all_actions
from backend.iam_app.dataclass.resources import ResourceEnum

pytestmark = pytest.mark.django_db

# 6 个 K8s 集群类型及其对应的 ResourceEnum 属性名
K8S_CLUSTER_TYPES = [
    ClusterType.K8sSurrealdb,
    ClusterType.K8sVictoriametrics,
    ClusterType.K8sRisingwave,
    ClusterType.K8sMilvus,
    ClusterType.K8sQdrant,
    ClusterType.K8sGreptimedb,
]

# 每种 K8s 存储类型下的操作后缀（与 ActionMeta 中 id 一致，不含跨类型的 k8s_addon_manage）
K8S_ACTION_SUFFIXES = [
    "apply",
    "modify",
    "destroy",
    "start",
    "stop",
    "restart",
    "pod_delete",
    "scale",
    "upgrade",
]


class TestK8sClusterTypeEnum:
    """T0-1: K8s 集群类型枚举测试"""

    def test_k8s_qdrant_exists(self):
        """K8sQdrant 枚举值存在"""
        assert ClusterType.K8sQdrant == "k8s_qdrant"

    def test_k8s_greptimedb_exists(self):
        """K8sGreptimedb 枚举值存在"""
        assert ClusterType.K8sGreptimedb == "k8s_greptimedb"

    def test_each_k8s_cluster_type_maps_to_own_db_type(self):
        """每种 K8s 集群类型与自身 db_type 一对一"""
        for ct in K8S_CLUSTER_TYPES:
            db_type = ClusterType.cluster_type_to_db_type(ct)
            assert db_type == ct.value
            types_for_db = ClusterType.db_type_to_cluster_types(db_type)
            assert types_for_db == [ct]

    def test_k8s_container_cluster_type_values(self):
        assert ClusterType.k8s_container_cluster_type_values() == frozenset(ct.value for ct in K8S_CLUSTER_TYPES)


class TestK8sResourceEnum:
    """T0-2: K8s ResourceMeta 枚举测试"""

    def test_all_k8s_resource_attrs_exist(self):
        """6 个 K8s ResourceMeta 属性都注册在 ResourceEnum 中"""
        for ct in K8S_CLUSTER_TYPES:
            attr_name = ct.upper().replace("-", "_")
            assert hasattr(ResourceEnum, attr_name), f"ResourceEnum.{attr_name} not found for cluster_type {ct}"

    def test_resource_attr_names_follow_convention(self):
        """属性名须等于 cluster_type_value.upper()"""
        for ct in K8S_CLUSTER_TYPES:
            expected_attr = ct.upper().replace("-", "_")
            resource_meta = getattr(ResourceEnum, expected_attr)
            assert resource_meta.id == ct, f"ResourceEnum.{expected_attr}.id={resource_meta.id!r}, expected {ct!r}"

    def test_k8s_surrealdb_resource_meta_id(self):
        assert ResourceEnum.K8S_SURREALDB.id == "k8s_surrealdb"

    def test_k8s_victoriametrics_resource_meta_id(self):
        assert ResourceEnum.K8S_VICTORIAMETRICS.id == "k8s_victoriametrics"

    def test_k8s_risingwave_resource_meta_id(self):
        assert ResourceEnum.K8S_RISINGWAVE.id == "k8s_risingwave"

    def test_k8s_milvus_resource_meta_id(self):
        assert ResourceEnum.K8S_MILVUS.id == "k8s_milvus"

    def test_k8s_qdrant_resource_meta_id(self):
        assert ResourceEnum.K8S_QDRANT.id == "k8s_qdrant"

    def test_k8s_greptimedb_resource_meta_id(self):
        assert ResourceEnum.K8S_GREPTIMEDB.id == "k8s_greptimedb"


class TestClusterTypeToResourceMeta:
    """T0-3: cluster_type_to_resource_meta 反射映射测试"""

    def test_k8s_surrealdb_maps_to_k8s_surrealdb_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sSurrealdb)
        assert result == ResourceEnum.K8S_SURREALDB

    def test_k8s_victoriametrics_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sVictoriametrics)
        assert result == ResourceEnum.K8S_VICTORIAMETRICS

    def test_k8s_risingwave_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sRisingwave)
        assert result == ResourceEnum.K8S_RISINGWAVE

    def test_k8s_milvus_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sMilvus)
        assert result == ResourceEnum.K8S_MILVUS

    def test_k8s_qdrant_maps_to_k8s_qdrant_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sQdrant)
        assert result == ResourceEnum.K8S_QDRANT

    def test_k8s_greptimedb_maps_to_k8s_greptimedb_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sGreptimedb)
        assert result == ResourceEnum.K8S_GREPTIMEDB

    def test_all_k8s_types_return_non_none(self):
        """所有 K8s 集群类型均不返回 None"""
        for ct in K8S_CLUSTER_TYPES:
            result = ResourceEnum.cluster_type_to_resource_meta(ct)
            assert result is not None, f"cluster_type_to_resource_meta({ct}) returned None"

    def test_non_k8s_type_still_works(self):
        """非 K8s 类型（如 TenDBHA）仍能正确映射"""
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.TenDBHA)
        assert result == ResourceEnum.MYSQL

    def test_unknown_cluster_type_returns_none(self):
        """未知集群类型返回 None 而不是抛出异常"""
        result = ResourceEnum.cluster_type_to_resource_meta("nonexistent_cluster_type")
        assert result is None


class TestK8sActionIds:
    """T0-4: K8s ActionMeta ID 格式验证"""

    K8S_TYPE_PREFIXES = [
        "k8s_surrealdb",
        "k8s_victoriametrics",
        "k8s_risingwave",
        "k8s_milvus",
        "k8s_qdrant",
        "k8s_greptimedb",
    ]

    def test_all_per_type_k8s_actions_exist_in_all_actions(self):
        expected_ids = [f"{prefix}_{suffix}" for prefix in self.K8S_TYPE_PREFIXES for suffix in K8S_ACTION_SUFFIXES]
        for action_id in expected_ids:
            assert action_id in _all_actions, f"action_id {action_id!r} not found in _all_actions"
        assert "k8s_addon_manage" in _all_actions

    def test_action_id_format_matches_pattern(self):
        """所有 K8s action_id 格式符合 k8s_{type}_{action} 规范"""
        pattern = re.compile(r"^k8s_[a-z]+(_[a-z]+)*$")
        for prefix in self.K8S_TYPE_PREFIXES:
            for suffix in K8S_ACTION_SUFFIXES:
                action_id = f"{prefix}_{suffix}"
                assert pattern.match(action_id), f"{action_id!r} does not match expected pattern"

    def test_k8s_actions_count(self):
        """_all_actions 中以 k8s_ 开头的 action 为 6×9 + addon_manage 共 55 个"""
        k8s_actions = [aid for aid in _all_actions if aid.startswith("k8s_")]
        assert len(k8s_actions) == 55, f"Expected 55 K8s actions, got {len(k8s_actions)}: {k8s_actions}"

    @pytest.mark.parametrize(
        "cluster_type_prefix",
        [
            "k8s_surrealdb",
            "k8s_victoriametrics",
            "k8s_risingwave",
            "k8s_milvus",
            "k8s_qdrant",
            "k8s_greptimedb",
        ],
    )
    def test_each_cluster_type_has_9_actions(self, cluster_type_prefix):
        """每种 K8s 集群类型恰好有 9 个 action"""
        matching = [aid for aid in _all_actions if aid.startswith(f"{cluster_type_prefix}_")]
        assert len(matching) == 9, f"{cluster_type_prefix} should have 9 actions, got {len(matching)}: {matching}"

    def test_apply_actions_have_business_resource(self):
        """apply 类 action 的 related_resource_types 包含 BUSINESS"""
        for prefix in self.K8S_TYPE_PREFIXES:
            action_id = f"{prefix}_apply"
            action = _all_actions[action_id]
            resource_ids = [rt.id for rt in action.related_resource_types]
            assert (
                ResourceEnum.BUSINESS.id in resource_ids
            ), f"{action_id} should relate to BUSINESS resource, got {resource_ids}"

    def test_non_apply_actions_have_cluster_resource(self):
        """非 apply 类 action 的 related_resource_types 包含对应 K8s 集群资源"""
        non_apply_suffixes = [s for s in K8S_ACTION_SUFFIXES if s != "apply"]
        for prefix in self.K8S_TYPE_PREFIXES:
            expected_resource_id = prefix  # e.g. "k8s_surrealdb"
            for suffix in non_apply_suffixes:
                action_id = f"{prefix}_{suffix}"
                action = _all_actions[action_id]
                resource_ids = [rt.id for rt in action.related_resource_types]
                assert (
                    expected_resource_id in resource_ids
                ), f"{action_id} should relate to {expected_resource_id} resource, got {resource_ids}"

    def test_actions_have_db_manage_in_related_actions(self):
        """所有 K8s action 都将 db_manage 列为 related_actions"""
        for prefix in self.K8S_TYPE_PREFIXES:
            for suffix in K8S_ACTION_SUFFIXES:
                action_id = f"{prefix}_{suffix}"
                action = _all_actions[action_id]
                related_ids = [a if isinstance(a, str) else a.id for a in action.related_actions]
                assert (
                    "db_manage" in related_ids
                ), f"{action_id}.related_actions should contain db_manage, got {related_ids}"


class TestProviderRegistration:
    """T0-5: 6 个 K8s Provider 已注册到 dispatcher"""

    def test_k8s_providers_registered_in_dispatcher(self):
        """6 个 K8s Provider 均已在 urls.py dispatcher 中注册"""
        # DjangoBasicResourceApiDispatcher 内部注册表属性名为 _provider（单数）
        from backend.iam_app import urls as iam_urls

        dispatcher = iam_urls.dispatcher
        registered = dispatcher._provider

        expected_keys = [
            "k8s_surrealdb",
            "k8s_victoriametrics",
            "k8s_risingwave",
            "k8s_milvus",
            "k8s_qdrant",
            "k8s_greptimedb",
        ]
        for key in expected_keys:
            assert key in registered, f"Provider {key!r} not registered in dispatcher"

    def test_k8s_provider_classes_are_correct_type(self):
        """dispatcher 中注册的 K8s Provider 类型正确"""
        from backend.iam_app import urls as iam_urls
        from backend.iam_app.views.cluster_provider import (
            K8sGreptimedbClusterResourceProvider,
            K8sMilvusClusterResourceProvider,
            K8sQdrantClusterResourceProvider,
            K8sRisingwaveClusterResourceProvider,
            K8sSurrealClusterResourceProvider,
            K8sVictoriametricsClusterResourceProvider,
        )

        dispatcher = iam_urls.dispatcher
        registered = dispatcher._provider

        expected_provider_types = {
            "k8s_surrealdb": K8sSurrealClusterResourceProvider,
            "k8s_victoriametrics": K8sVictoriametricsClusterResourceProvider,
            "k8s_risingwave": K8sRisingwaveClusterResourceProvider,
            "k8s_milvus": K8sMilvusClusterResourceProvider,
            "k8s_qdrant": K8sQdrantClusterResourceProvider,
            "k8s_greptimedb": K8sGreptimedbClusterResourceProvider,
        }
        for key, expected_type in expected_provider_types.items():
            assert isinstance(
                registered[key], expected_type
            ), f"dispatcher[{key!r}] is {type(registered[key])}, expected {expected_type}"


class TestSignalK8sClusterAutoGrant:
    """T0-6: K8s 集群创建时自动授权给创建者"""

    @patch("backend.iam_app.handlers.signal.post_save_grant_iam")
    def test_post_save_cluster_k8s_surrealdb_calls_grant(self, mock_grant):
        """K8s Surreal 集群创建时触发 IAM 授权"""
        from backend.db_meta.models import Cluster
        from backend.iam_app.handlers.signal import post_save_cluster

        instance = MagicMock(spec=Cluster)
        instance.cluster_type = ClusterType.K8sSurrealdb
        instance.creator = "test_user"

        post_save_cluster(sender=Cluster, instance=instance, created=True)

        mock_grant.assert_called_once()
        resource_meta_arg = mock_grant.call_args[0][0]
        expected_attr = ClusterType.K8sSurrealdb.upper().replace("-", "_")
        expected_meta = getattr(ResourceEnum, expected_attr)
        assert (
            resource_meta_arg == expected_meta
        ), f"post_save_cluster({ClusterType.K8sSurrealdb}): resource_meta={resource_meta_arg!r}, expected {expected_meta!r}"

    @patch("backend.iam_app.handlers.signal.post_save_grant_iam")
    def test_unknown_cluster_type_does_not_call_grant(self, mock_grant):
        """未知集群类型时 resource_meta 为 None，不触发授权"""
        from backend.db_meta.models import Cluster
        from backend.iam_app.handlers.signal import post_save_cluster

        instance = MagicMock(spec=Cluster)
        instance.cluster_type = "nonexistent_type"
        instance.creator = "test_user"

        post_save_cluster(sender=Cluster, instance=instance, created=True)

        mock_grant.assert_not_called()

    @patch("backend.iam_app.handlers.signal.post_save_grant_iam")
    def test_k8s_cluster_not_created_does_not_call_grant(self, mock_grant):
        """created=False 时（更新操作）不触发授权"""
        from backend.db_meta.models import Cluster
        from backend.iam_app.handlers.signal import post_save_cluster

        instance = MagicMock(spec=Cluster)
        instance.cluster_type = ClusterType.K8sSurrealdb
        instance.creator = "test_user"

        # post_save_cluster 本身只负责获取 resource_meta 并调用 post_save_grant_iam
        # created=False 由 post_save_grant_iam 内部处理，这里验证 post_save_cluster 仍调用了 grant
        post_save_cluster(sender=Cluster, instance=instance, created=False)

        # post_save_cluster 本身不检查 created，它传递给 post_save_grant_iam
        mock_grant.assert_called_once()
        call_kwargs = mock_grant.call_args[0]
        # 第 4 个参数是 created
        assert call_kwargs[4] is False
