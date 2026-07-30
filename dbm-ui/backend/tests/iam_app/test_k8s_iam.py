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

# 7 个 K8s 集群类型（SurrealDB 拆为 HA + Single，其余均为 HA）
K8S_CLUSTER_TYPES = [
    ClusterType.K8sSurrealdbHa,
    ClusterType.K8sSurrealdbSingle,
    ClusterType.K8sVictoriametricsHa,
    ClusterType.K8sRisingwaveHa,
    ClusterType.K8sMilvusHa,
    ClusterType.K8sQdrantHa,
    ClusterType.K8sGreptimedbHa,
]

# 所有 K8s 存储类型的统一操作集（SurrealDB / Qdrant 与其余类型均使用相同集合）
# 含 view/edit/apply/destroy/enable_disable/manage，不含 modify/start/stop/restart/pod_delete/scale/upgrade
K8S_ACTION_SUFFIXES = [
    "view",
    "edit",
    "apply",
    "destroy",
    "enable_disable",
    "manage",
]

# 各 K8s 类型预期操作集（全部统一为 6 个操作）
K8S_TYPE_ACTIONS = {
    "k8s_surrealdb": K8S_ACTION_SUFFIXES,
    "k8s_victoriametrics": K8S_ACTION_SUFFIXES,
    "k8s_risingwave": K8S_ACTION_SUFFIXES,
    "k8s_milvus": K8S_ACTION_SUFFIXES,
    "k8s_qdrant": K8S_ACTION_SUFFIXES,
    "k8s_greptimedb": K8S_ACTION_SUFFIXES,
}

# IAM 限制 action id 最长 32 字符，victoriametrics 的 db_type 名过长，
# 其 action id 前缀使用缩写 k8s_vm（其余类型 action 前缀与 db_type 一致）
K8S_ACTION_ID_PREFIX = {
    "k8s_surrealdb": "k8s_surrealdb",
    "k8s_victoriametrics": "k8s_vm",
    "k8s_risingwave": "k8s_risingwave",
    "k8s_milvus": "k8s_milvus",
    "k8s_qdrant": "k8s_qdrant",
    "k8s_greptimedb": "k8s_greptimedb",
}


class TestK8sClusterTypeEnum:
    """T0-1: K8s 集群类型枚举测试"""

    def test_k8s_surrealdb_ha_exists(self):
        assert ClusterType.K8sSurrealdbHa == "k8s_surrealdb_ha"

    def test_k8s_surrealdb_single_exists(self):
        assert ClusterType.K8sSurrealdbSingle == "k8s_surrealdb_single"

    def test_k8s_qdrant_ha_exists(self):
        assert ClusterType.K8sQdrantHa == "k8s_qdrant_ha"

    def test_k8s_greptimedb_ha_exists(self):
        assert ClusterType.K8sGreptimedbHa == "k8s_greptimedb_ha"

    def test_surrealdb_maps_to_shared_db_type(self):
        """SurrealDB HA/Single 均映射到同一 db_type"""
        for ct in [ClusterType.K8sSurrealdbHa, ClusterType.K8sSurrealdbSingle]:
            db_type = ClusterType.cluster_type_to_db_type(ct)
            assert db_type == "k8s_surrealdb"
        types_for_db = ClusterType.db_type_to_cluster_types("k8s_surrealdb")
        assert ClusterType.K8sSurrealdbHa in types_for_db
        assert ClusterType.K8sSurrealdbSingle in types_for_db

    def test_each_ha_only_k8s_cluster_type_maps_to_db_type(self):
        """HA-only 集群类型映射到各自 db_type"""
        ha_only = {
            ClusterType.K8sVictoriametricsHa: "k8s_victoriametrics",
            ClusterType.K8sRisingwaveHa: "k8s_risingwave",
            ClusterType.K8sMilvusHa: "k8s_milvus",
            ClusterType.K8sQdrantHa: "k8s_qdrant",
            ClusterType.K8sGreptimedbHa: "k8s_greptimedb",
        }
        for ct, expected_db_type in ha_only.items():
            db_type = ClusterType.cluster_type_to_db_type(ct)
            assert db_type == expected_db_type
            types_for_db = ClusterType.db_type_to_cluster_types(expected_db_type)
            assert types_for_db == [ct]

    def test_k8s_container_cluster_type_values(self):
        assert ClusterType.k8s_container_cluster_type_values() == frozenset(ct.value for ct in K8S_CLUSTER_TYPES)


class TestK8sResourceEnum:
    """T0-2: K8s ResourceMeta 枚举测试（ResourceMeta 仍在 DBType 粒度，不随 HA/Single 拆分）"""

    K8S_RESOURCE_ATTRS = [
        "K8S_SURREALDB",
        "K8S_VICTORIAMETRICS",
        "K8S_RISINGWAVE",
        "K8S_MILVUS",
        "K8S_QDRANT",
        "K8S_GREPTIMEDB",
    ]

    def test_all_k8s_resource_attrs_exist(self):
        """6 个 K8s ResourceMeta 属性都注册在 ResourceEnum 中"""
        for attr_name in self.K8S_RESOURCE_ATTRS:
            assert hasattr(ResourceEnum, attr_name), f"ResourceEnum.{attr_name} not found"

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
    """T0-3: cluster_type_to_resource_meta 反射映射测试（HA/Single 共享同一 ResourceMeta）"""

    def test_surrealdb_ha_maps_to_k8s_surrealdb_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sSurrealdbHa)
        assert result == ResourceEnum.K8S_SURREALDB

    def test_surrealdb_single_maps_to_k8s_surrealdb_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sSurrealdbSingle)
        assert result == ResourceEnum.K8S_SURREALDB

    def test_k8s_victoriametrics_ha_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sVictoriametricsHa)
        assert result == ResourceEnum.K8S_VICTORIAMETRICS

    def test_k8s_risingwave_ha_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sRisingwaveHa)
        assert result == ResourceEnum.K8S_RISINGWAVE

    def test_k8s_milvus_ha_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sMilvusHa)
        assert result == ResourceEnum.K8S_MILVUS

    def test_k8s_qdrant_ha_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sQdrantHa)
        assert result == ResourceEnum.K8S_QDRANT

    def test_k8s_greptimedb_ha_maps_to_resource(self):
        result = ResourceEnum.cluster_type_to_resource_meta(ClusterType.K8sGreptimedbHa)
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

    K8S_TYPE_PREFIXES = list(K8S_TYPE_ACTIONS.keys())

    def test_all_per_type_k8s_actions_exist_in_all_actions(self):
        for prefix, suffixes in K8S_TYPE_ACTIONS.items():
            action_prefix = K8S_ACTION_ID_PREFIX[prefix]
            for suffix in suffixes:
                action_id = f"{action_prefix}_{suffix}"
                assert action_id in _all_actions, f"action_id {action_id!r} not found in _all_actions"
        assert "k8s_addon_manage" in _all_actions

    def test_action_id_format_matches_pattern(self):
        """所有 K8s action_id 格式符合 k8s_{type}_{action} 规范"""
        pattern = re.compile(r"^k8s_[a-z]+(_[a-z]+)*$")
        for prefix, suffixes in K8S_TYPE_ACTIONS.items():
            action_prefix = K8S_ACTION_ID_PREFIX[prefix]
            for suffix in suffixes:
                action_id = f"{action_prefix}_{suffix}"
                assert pattern.match(action_id), f"{action_id!r} does not match expected pattern"

    def test_k8s_actions_count(self):
        """_all_actions 中以 k8s_ 开头的 action 为 37 个（6 个类型各 6 个，加 addon_manage）"""
        k8s_actions = [aid for aid in _all_actions if aid.startswith("k8s_")]
        assert len(k8s_actions) == 37, f"Expected 37 K8s actions, got {len(k8s_actions)}: {k8s_actions}"

    @pytest.mark.parametrize(
        "cluster_type_prefix",
        list(K8S_TYPE_ACTIONS.keys()),
    )
    def test_each_cluster_type_has_6_actions(self, cluster_type_prefix):
        """每种 K8s 集群类型 action 数均为 6 个（统一操作集 view/edit/apply/destroy/enable_disable/manage）"""
        action_prefix = K8S_ACTION_ID_PREFIX[cluster_type_prefix]
        matching = [aid for aid in _all_actions if aid.startswith(f"{action_prefix}_")]
        expected_suffixes = K8S_TYPE_ACTIONS[cluster_type_prefix]
        assert len(matching) == len(expected_suffixes), (
            f"{cluster_type_prefix} should have {len(expected_suffixes)} actions, " f"got {len(matching)}: {matching}"
        )

    def test_apply_actions_have_business_resource(self):
        """apply 类 action 的 related_resource_types 包含 BUSINESS"""
        for prefix in self.K8S_TYPE_PREFIXES:
            action_id = f"{K8S_ACTION_ID_PREFIX[prefix]}_apply"
            action = _all_actions[action_id]
            resource_ids = [rt.id for rt in action.related_resource_types]
            assert (
                ResourceEnum.BUSINESS.id in resource_ids
            ), f"{action_id} should relate to BUSINESS resource, got {resource_ids}"

    def test_non_apply_actions_have_cluster_resource(self):
        """非 apply 类 action 的 related_resource_types 包含对应 K8s 集群资源"""
        for prefix in self.K8S_TYPE_PREFIXES:
            expected_resource_id = prefix  # e.g. "k8s_surrealdb"（resource id 与 db_type 一致）
            action_prefix = K8S_ACTION_ID_PREFIX[prefix]
            non_apply_suffixes = [s for s in K8S_TYPE_ACTIONS[prefix] if s != "apply"]
            for suffix in non_apply_suffixes:
                action_id = f"{action_prefix}_{suffix}"
                action = _all_actions[action_id]
                resource_ids = [rt.id for rt in action.related_resource_types]
                assert (
                    expected_resource_id in resource_ids
                ), f"{action_id} should relate to {expected_resource_id} resource, got {resource_ids}"

    def test_actions_have_db_manage_in_related_actions(self):
        """所有 K8s action 都将 db_manage 列为 related_actions（enable_disable/manage 除外，它们遵循已有模式引用对应 _view）"""
        for prefix in self.K8S_TYPE_PREFIXES:
            action_prefix = K8S_ACTION_ID_PREFIX[prefix]
            for suffix in K8S_TYPE_ACTIONS[prefix]:
                # enable_disable/manage 遵循代码库已有模式仅引用对应 _view（如 MYSQL_ENABLE_DISABLE → MYSQL_VIEW）
                if suffix in ("enable_disable", "manage"):
                    continue
                action_id = f"{action_prefix}_{suffix}"
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
    def test_post_save_cluster_k8s_surrealdb_ha_calls_grant(self, mock_grant):
        """K8s SurrealDB HA 集群创建时触发 IAM 授权"""
        from backend.db_meta.models import Cluster
        from backend.iam_app.handlers.signal import post_save_cluster

        instance = MagicMock(spec=Cluster)
        instance.cluster_type = ClusterType.K8sSurrealdbHa
        instance.creator = "test_user"

        post_save_cluster(sender=Cluster, instance=instance, created=True)

        mock_grant.assert_called_once()
        resource_meta_arg = mock_grant.call_args[0][0]
        assert (
            resource_meta_arg == ResourceEnum.K8S_SURREALDB
        ), f"post_save_cluster(K8sSurrealdbHa): resource_meta={resource_meta_arg!r}, expected K8S_SURREALDB"

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
        instance.cluster_type = ClusterType.K8sSurrealdbHa
        instance.creator = "test_user"

        post_save_cluster(sender=Cluster, instance=instance, created=False)

        # post_save_cluster 本身不检查 created，它传递给 post_save_grant_iam
        mock_grant.assert_called_once()
        call_kwargs = mock_grant.call_args[0]
        # 第 4 个参数是 created
        assert call_kwargs[4] is False
