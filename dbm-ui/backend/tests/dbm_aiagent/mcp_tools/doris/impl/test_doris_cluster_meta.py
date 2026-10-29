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
# 本文件覆盖 Doris 元数据的角色分桶、零角色省略、层汇总与序列化器契约。
# 统计逻辑做成接受实例序列的纯函数，用轻量假对象数据驱动测试；
# 涉及 ORM 的入口一律 mock，用例自身不访问数据库。
#
# 注意：backend/tests/conftest.py 中存在若干 scope="session" 且 autouse=True 的
# 数据库初始化 fixture，因此运行本文件仍需可用的 MySQL 与
# ENABLE_DBM_AI=true（dbm_aiagent 应用仅在该开关下注册进 INSTALLED_APPS）。
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.db_meta.enums import ClusterType, InstanceRole, MachineType
from backend.dbm_aiagent.mcp_tools.doris.enums import BE_ROLES, FE_ROLES
from backend.dbm_aiagent.mcp_tools.doris.impl import cluster_meta as mod
from backend.dbm_aiagent.mcp_tools.doris.serializers.cluster_meta import (
    DorisBizInputSerializer,
    DorisBizNameInputSerializer,
    DorisClusterInputSerializer,
    DorisClusterListOutputSerializer,
    DorisClusterOverviewOutputSerializer,
    DorisSpecSearchInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpClusterNotFoundException

CLUSTER_DOMAIN = "doris.test.dba.db"

_SPEC_DETAILS = {
    1: {
        "spec_id": 1,
        "spec_name": "16核32G",
        "cpu": {"min": 16, "max": 16},
        "mem": {"min": 32, "max": 32},
        "storage_spec": [],
        "device_class": [],
        "desc": "",
    },
    2: {
        "spec_id": 2,
        "spec_name": "8核16G",
        "cpu": {"min": 8, "max": 8},
        "mem": {"min": 16, "max": 16},
        "storage_spec": [],
        "device_class": [],
        "desc": "",
    },
}


def make_instance(
    instance_role,
    bk_host_id,
    machine_type=MachineType.DORIS_BACKEND.value,
    status="running",
    version="2.0.3",
    spec_id=1,
    bk_os_name="linux",
    bk_sub_zone="zone-a",
    device_class="SA5",
):
    """构造轻量假实例，字段与 StorageInstance / Machine 实际字段名一致。"""
    return SimpleNamespace(
        instance_role=instance_role,
        machine_type=machine_type,
        status=status,
        version=version,
        machine=SimpleNamespace(
            bk_host_id=bk_host_id,
            spec_id=spec_id,
            bk_os_name=bk_os_name,
            bk_sub_zone=bk_sub_zone,
            bk_svr_device_cls_name=device_class,
        ),
    )


class TestRoleBucketing:
    """分桶必须以 instance_role 为准。

    Doris 的 BE 热/温/冷三个角色共用同一个 machine_type(doris_backend)，
    用 machine_type 分组会把三类节点混成一桶，丢失冷热分层。
    """

    def test_be_roles_split_despite_same_machine_type(self):
        instances = [
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 1),
            make_instance(InstanceRole.DORIS_BACKEND_WARM.value, 2),
            make_instance(InstanceRole.DORIS_BACKEND_COLD.value, 3),
        ]
        # 三者 machine_type 相同，验证前提成立
        assert len({one.machine_type for one in instances}) == 1

        stats = mod.build_role_stats(instances, _SPEC_DETAILS)
        assert set(stats) == {
            InstanceRole.DORIS_BACKEND_HOT.value,
            InstanceRole.DORIS_BACKEND_WARM.value,
            InstanceRole.DORIS_BACKEND_COLD.value,
        }
        for one_stat in stats.values():
            assert one_stat["node_count"] == 1

    def test_fe_and_be_layers_tagged(self):
        instances = [
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 1, MachineType.DORIS_FOLLOWER.value),
            make_instance(InstanceRole.DORIS_OBSERVER.value, 2, MachineType.DORIS_OBSERVER.value),
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 3),
        ]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)
        assert stats[InstanceRole.DORIS_FOLLOWER.value]["layer"] == "fe"
        assert stats[InstanceRole.DORIS_OBSERVER.value]["layer"] == "fe"
        assert stats[InstanceRole.DORIS_BACKEND_HOT.value]["layer"] == "be"

    def test_role_alias_from_instance_role_enum(self):
        """角色中文名取自 InstanceRole 枚举，不自行编造。"""
        stats = mod.build_role_stats([make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 1)], _SPEC_DETAILS)
        expected = dict(InstanceRole.get_choices())[InstanceRole.DORIS_BACKEND_HOT.value]
        assert stats[InstanceRole.DORIS_BACKEND_HOT.value]["role_alias"] == str(expected)

    def test_machine_count_dedup_by_host(self):
        """同一台机器承载多个实例时，机器维度统计需按 bk_host_id 去重。"""
        instances = [
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 7),
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 7),
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 8),
        ]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)[InstanceRole.DORIS_BACKEND_HOT.value]
        assert stats["node_count"] == 3
        assert stats["machine_count"] == 2
        # 规格、OS、Zone、机型均为机器维度，同样去重
        assert sum(stats["by_spec"].values()) == 2
        assert sum(stats["by_os"].values()) == 2
        assert sum(stats["by_sub_zone"].values()) == 2
        assert sum(stats["by_device_class"].values()) == 2

    def test_status_and_version_aggregated(self):
        instances = [
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 1, status="running", version="2.0.3"),
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 2, status="unavailable", version="2.0.4"),
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 3, status="running", version="2.0.3"),
        ]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)[InstanceRole.DORIS_FOLLOWER.value]
        assert stats["by_status"] == {"running": 2, "unavailable": 1}
        assert stats["versions"] == ["2.0.3", "2.0.4"]

    def test_spec_details_keyed_by_int_and_scoped_to_role(self):
        """spec_details 用 int 型 spec_id 做键，且只含该角色实际用到的规格。"""
        instances = [
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 1, spec_id=1),
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 2, spec_id=2),
        ]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)
        fe_stats = stats[InstanceRole.DORIS_FOLLOWER.value]
        be_stats = stats[InstanceRole.DORIS_BACKEND_HOT.value]

        assert list(fe_stats["spec_details"]) == [1]
        assert list(be_stats["spec_details"]) == [2]
        assert all(isinstance(key, int) for key in fe_stats["by_spec"])
        assert fe_stats["spec_details"][1]["spec_name"] == "16核32G"

    def test_missing_spec_id_not_counted(self):
        """spec_id 为 0（未登记规格）不应产生 by_spec 条目。"""
        stats = mod.build_role_stats([make_instance(InstanceRole.DORIS_FOLLOWER.value, 1, spec_id=0)], _SPEC_DETAILS)
        assert stats[InstanceRole.DORIS_FOLLOWER.value]["by_spec"] == {}
        assert stats[InstanceRole.DORIS_FOLLOWER.value]["spec_details"] == {}


class TestZeroRoleOmitted:
    """未部署的角色不应出现在结果中。

    用户明确要求：Observer 实际几乎不用、温节点也未验证有数据，
    输出空占位只是累赘。省略优先于结构对称。
    """

    def test_only_deployed_roles_present(self):
        instances = [
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 1, MachineType.DORIS_FOLLOWER.value),
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 2),
        ]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)

        assert set(stats) == {
            InstanceRole.DORIS_FOLLOWER.value,
            InstanceRole.DORIS_BACKEND_HOT.value,
        }
        assert InstanceRole.DORIS_OBSERVER.value not in stats
        assert InstanceRole.DORIS_BACKEND_WARM.value not in stats
        assert InstanceRole.DORIS_BACKEND_COLD.value not in stats

    def test_no_zero_node_count_entry(self):
        instances = [make_instance(InstanceRole.DORIS_FOLLOWER.value, 1)]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)
        assert all(one["node_count"] > 0 for one in stats.values())

    def test_empty_cluster_returns_empty_roles(self):
        """集群无实例时返回空字典且不抛异常。"""
        assert mod.build_role_stats([], {}) == {}


class TestLayerSummary:
    def test_summary_matches_role_details(self):
        instances = [
            make_instance(InstanceRole.DORIS_FOLLOWER.value, 1, MachineType.DORIS_FOLLOWER.value),
            make_instance(InstanceRole.DORIS_OBSERVER.value, 2, MachineType.DORIS_OBSERVER.value),
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 3),
            make_instance(InstanceRole.DORIS_BACKEND_COLD.value, 4),
            make_instance(InstanceRole.DORIS_BACKEND_COLD.value, 5),
        ]
        stats = mod.build_role_stats(instances, _SPEC_DETAILS)
        summary = mod.build_layer_summary(instances)

        fe_nodes = sum(one["node_count"] for one in stats.values() if one["layer"] == "fe")
        be_nodes = sum(one["node_count"] for one in stats.values() if one["layer"] == "be")
        assert summary["fe_node_count"] == fe_nodes == 2
        assert summary["be_node_count"] == be_nodes == 3
        assert summary["total_node_count"] == 5
        assert summary["total_machine_count"] == 5

    def test_summary_machine_dedup(self):
        instances = [
            make_instance(InstanceRole.DORIS_BACKEND_HOT.value, 1),
            make_instance(InstanceRole.DORIS_BACKEND_COLD.value, 1),
        ]
        summary = mod.build_layer_summary(instances)
        assert summary["be_node_count"] == 2
        # 两个实例同机，BE 层机器数与全集群机器数都应为 1
        assert summary["be_machine_count"] == 1
        assert summary["total_machine_count"] == 1

    def test_empty_summary_all_zero(self):
        summary = mod.build_layer_summary([])
        assert set(summary.values()) == {0}

    def test_role_layer_helper_covers_all_doris_roles(self):
        """五个 Doris 角色都应被归入 fe 或 be，不能落到 unknown。"""
        for role in FE_ROLES:
            assert mod._role_layer(role) == "fe"
        for role in BE_ROLES:
            assert mod._role_layer(role) == "be"
        assert mod._role_layer("not_a_doris_role") == "unknown"


class TestClusterValidation:
    def test_cluster_not_found(self):
        with patch.object(mod, "Cluster") as mock_cluster:
            mock_cluster.objects.prefetch_related.return_value.filter.return_value.first.return_value = None
            mock_cluster.objects.filter.return_value.first.return_value = None

            with pytest.raises(DBMMcpClusterNotFoundException) as exc_info:
                mod.validate_doris_cluster(CLUSTER_DOMAIN)

        assert CLUSTER_DOMAIN in str(exc_info.value)

    def test_cluster_type_mismatch_message_differs(self):
        """域名存在但非 Doris 集群时，提示需与「域名不存在」可区分。"""
        other = SimpleNamespace(cluster_type=ClusterType.TenDBHA.value)
        with patch.object(mod, "Cluster") as mock_cluster:
            mock_cluster.objects.prefetch_related.return_value.filter.return_value.first.return_value = None
            mock_cluster.objects.filter.return_value.first.return_value = other

            with pytest.raises(DBMMcpClusterNotFoundException) as exc_info:
                mod.validate_doris_cluster(CLUSTER_DOMAIN)

        message = str(exc_info.value)
        assert ClusterType.TenDBHA.value in message
        assert "Doris" in message

    def test_valid_doris_cluster_returned(self):
        cluster = SimpleNamespace(cluster_type=ClusterType.Doris.value, immute_domain=CLUSTER_DOMAIN)
        with patch.object(mod, "Cluster") as mock_cluster:
            mock_cluster.objects.prefetch_related.return_value.filter.return_value.first.return_value = cluster
            assert mod.validate_doris_cluster(CLUSTER_DOMAIN) is cluster


class TestListMyBizs:
    def test_no_managed_biz_converted_to_readable_error(self):
        """get_managed_biz 抛裸 ValueError，需转为带下一步建议的可读错误。"""
        with patch.object(mod, "get_managed_biz", side_effect=ValueError("boom")):
            with pytest.raises(DBMMcpBaseException) as exc_info:
                mod.list_my_doris_bizs("someone")

        message = str(exc_info.value)
        assert "someone" in message
        assert "bk_biz_id" in message

    def test_managed_biz_passthrough(self):
        expected = [{"bk_biz_id": 3, "app_name": "dba", "abbr": "dba"}]
        with patch.object(mod, "get_managed_biz", return_value=expected) as mocked:
            assert mod.list_my_doris_bizs("admin") == expected

        # 必须传 DBType.Doris，传错会查到其他组件的业务
        assert mocked.call_args.args[1] == mod.DBType.Doris


class TestSerializerContract:
    def test_overview_keys_declared(self):
        """实际返回键必须都在 serializer 中声明，避免文档与实现脱节。"""
        cluster = SimpleNamespace(
            id=1,
            bk_biz_id=3,
            bk_cloud_id=0,
            immute_domain=CLUSTER_DOMAIN,
            alias="test",
            cluster_type=ClusterType.Doris.value,
            major_version="2.0.3",
            phase="online",
            region="sh",
            disaster_tolerance_level="NONE",
            tags=SimpleNamespace(all=lambda: []),
        )
        instances = [make_instance(InstanceRole.DORIS_FOLLOWER.value, 1)]

        with patch.object(mod, "validate_doris_cluster", return_value=cluster), patch.object(
            mod, "StorageInstance"
        ) as mock_si, patch.object(mod, "ClusterEntry") as mock_entry, patch.object(
            mod, "_collect_spec_details", return_value=_SPEC_DETAILS
        ):
            mock_si.objects.filter.return_value.select_related.return_value = instances
            mock_entry.objects.filter.return_value = []
            result = mod.cluster_overview(CLUSTER_DOMAIN)

        declared = set(DorisClusterOverviewOutputSerializer().fields)
        assert set(result) <= declared, "未声明的响应字段: {}".format(set(result) - declared)
        assert result["cluster_domain"] == CLUSTER_DOMAIN
        # 概览不返回逐节点清单
        assert "nodes" not in result
        for one_role in result["roles"].values():
            assert "nodes" not in one_role

    def test_cluster_list_keys_declared(self):
        cluster = SimpleNamespace(
            id=1,
            bk_biz_id=3,
            bk_cloud_id=0,
            cluster_type=ClusterType.Doris.value,
            immute_domain=CLUSTER_DOMAIN,
            alias="test",
            region="sh",
            major_version="2.0.3",
        )
        counted = [{"cluster__id": 1, "instance_role": InstanceRole.DORIS_FOLLOWER.value, "node_count": 3}]

        with patch.object(mod, "Cluster") as mock_cluster, patch.object(mod, "StorageInstance") as mock_si:
            mock_cluster.objects.filter.return_value = [cluster]
            mock_si.objects.filter.return_value.values.return_value.annotate.return_value = counted
            result = mod.doris_list_clusters(bk_biz_id=3)

        declared = set(DorisClusterListOutputSerializer().fields)
        assert result and set(result[0]) <= declared
        assert result[0]["role_node_counts"] == {InstanceRole.DORIS_FOLLOWER.value: 3}

    def test_cluster_list_empty_biz(self):
        with patch.object(mod, "Cluster") as mock_cluster:
            mock_cluster.objects.filter.return_value = []
            assert mod.doris_list_clusters(bk_biz_id=999) == []

    def test_input_serializer_required_fields(self):
        assert not DorisClusterInputSerializer(data={}).is_valid()
        assert not DorisBizInputSerializer(data={}).is_valid()
        assert not DorisBizNameInputSerializer(data={}).is_valid()
        assert not DorisSpecSearchInputSerializer(data={}).is_valid()

        slz = DorisClusterInputSerializer(data={"cluster_domain": CLUSTER_DOMAIN})
        assert slz.is_valid(), slz.errors
        assert slz.validated_data["cluster_domain"] == CLUSTER_DOMAIN

    def test_cluster_domain_naming_consistent_with_metrics_tool(self):
        """入参名与同组件的指标工具保持一致，避免智能体在两个 server 间反复试错。"""
        from backend.dbm_aiagent.mcp_tools.doris.serializers.doris_metrics import DorisMetricsInputSerializer

        assert "cluster_domain" in DorisClusterInputSerializer().fields
        assert "cluster_domain" in DorisMetricsInputSerializer().fields
        assert "immute_domain" not in DorisClusterInputSerializer().fields


class TestNoMonitoringDependency:
    """元数据模块不得引入监控依赖，使用量信息由指标工具提供。"""

    # 检查 import 语句与模块命名空间，而非源码全文 —— 后者会误伤
    # docstring 中「本模块不引入 XXX」这类说明性文字。
    FORBIDDEN_NAMES = ("BKMonitorV3Api", "execute_promql", "PromQLQueryBuilder", "PromQLMultiQueryBuilder")

    def _import_statements(self):
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(mod))
        statements = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                statements.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                statements.extend(f"{module}.{alias.name}" for alias in node.names)
        return statements

    def test_no_monitor_symbol_in_namespace(self):
        for forbidden in self.FORBIDDEN_NAMES:
            assert not hasattr(mod, forbidden), f"元数据模块不应引用监控模块: {forbidden}"

    def test_no_monitor_import_statement(self):
        statements = self._import_statements()
        for one_import in statements:
            assert "promql" not in one_import.lower(), f"元数据模块不应导入监控模块: {one_import}"
            assert "BKMonitor" not in one_import, f"元数据模块不应导入监控模块: {one_import}"
            assert "components" not in one_import, f"元数据模块不应导入外部组件客户端: {one_import}"

    def test_does_not_import_mysql_component(self):
        for one_import in self._import_statements():
            assert "mcp_tools.mysql" not in one_import, f"不应引用 mysql 组件: {one_import}"

    def test_does_not_import_other_component_impl(self):
        """组件间保持独立，不跨组件复用 impl 实现。"""
        for one_import in self._import_statements():
            for component in ("kafka", "pulsar", "redis", "mongodb"):
                assert f"mcp_tools.{component}" not in one_import, f"不应跨组件引用: {one_import}"
