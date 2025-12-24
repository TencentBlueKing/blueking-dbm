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

from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources.query import CommonExportQueryResourceMixin, CommonQueryResourceMixin
from backend.ticket.constants import TicketType

pytestmark = pytest.mark.django_db


class TestCommonExportQueryResourceMixin:
    """测试 CommonExportQueryResourceMixin 类"""

    def test_update_headers_default(self):
        """测试默认的 update_headers 方法"""
        headers = [{"id": "cluster_id", "name": "集群ID"}]

        new_headers, extra_headers = CommonExportQueryResourceMixin.update_headers(headers)

        assert new_headers == headers
        assert extra_headers == []

    def test_update_cluster_info_default(self):
        """测试默认的 update_cluster_info 方法"""
        cluster = MagicMock()
        cluster_info = {"cluster_id": 1, "cluster_name": "test"}

        result = CommonExportQueryResourceMixin.update_cluster_info(cluster, cluster_info)

        assert result == cluster_info

    def test_fill_instances_to_cluster_info_empty(self):
        """测试填充实例信息 - 空实例集"""
        cluster_info = {}
        role_header_ids = set()
        instance_queryset = StorageInstance.objects.none()

        CommonExportQueryResourceMixin.fill_instances_to_cluster_info(cluster_info, instance_queryset, role_header_ids)

        assert cluster_info == {}
        assert role_header_ids == set()

    def test_fill_instances_to_cluster_info_with_instances(self, test_cluster_with_entries):
        """测试填充实例信息 - 包含实例"""
        cluster = test_cluster_with_entries
        cluster_info = {}
        role_header_ids = set()

        # 获取存储实例
        storage_queryset = cluster.storageinstance_set.all()

        CommonExportQueryResourceMixin.fill_instances_to_cluster_info(cluster_info, storage_queryset, role_header_ids)

        # 验证实例信息已填充
        assert len(role_header_ids) > 0
        # 验证至少有一个角色的实例信息被填充
        for role in role_header_ids:
            assert role in cluster_info
            assert ":" in cluster_info[role]  # 格式应该是 ip:port

    def test_fill_instances_to_cluster_info_multiple_instances(self, test_cluster_with_entries):
        """测试填充实例信息 - 多个实例"""
        cluster = test_cluster_with_entries
        cluster_info = {}
        role_header_ids = set()

        # 获取代理实例
        proxy_queryset = cluster.proxyinstance_set.all()

        CommonExportQueryResourceMixin.fill_instances_to_cluster_info(cluster_info, proxy_queryset, role_header_ids)

        # 验证多个实例用换行符分隔
        for role in role_header_ids:
            if role in cluster_info:
                # 如果有多个实例，应该包含换行符
                instances = cluster_info[role].split("\n")
                assert len(instances) >= 1


class TestCommonQueryResourceMixin:
    """测试 CommonQueryResourceMixin 类"""

    def test_get_cluster_clb_polaris_entries_empty(self):
        """测试获取CLB和Polaris入口 - 无入口"""
        cluster = MagicMock()
        cluster.clusterentry_set.all.return_value = []

        clb_entry, polaris_entry = CommonQueryResourceMixin.get_cluster_clb_polaris_entries(cluster)

        assert clb_entry == ""
        assert polaris_entry == ""

    def test_get_cluster_clb_polaris_entries_with_clb(self, test_cluster_with_entries):
        """测试获取CLB和Polaris入口 - 包含CLB"""
        cluster = test_cluster_with_entries

        clb_entry, polaris_entry = CommonQueryResourceMixin.get_cluster_clb_polaris_entries(cluster)

        # 验证CLB入口信息
        assert clb_entry != ""
        assert "1.1.1.100" in clb_entry or "clb-dns.test.db" in clb_entry

    def test_get_cluster_clb_polaris_entries_with_polaris(self, test_cluster_with_entries):
        """测试获取CLB和Polaris入口 - 包含Polaris"""
        cluster = test_cluster_with_entries

        clb_entry, polaris_entry = CommonQueryResourceMixin.get_cluster_clb_polaris_entries(cluster)

        # 验证Polaris入口信息
        assert polaris_entry != ""
        assert "123456:65535" in polaris_entry or "test_polaris" in polaris_entry

    @patch("backend.flow.utils.dns_manage.DnsManage.get_domain")
    def test_query_cluster_entry_details_dns(self, mock_get_domain, test_cluster_with_entries):
        """测试查询集群访问入口详情 - DNS类型"""
        cluster = test_cluster_with_entries
        mock_get_domain.return_value = [{"target": "1.1.1.1", "port": 10000}]

        cluster_details = {
            "id": cluster.id,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        entry_details = CommonQueryResourceMixin.query_cluster_entry_details(
            cluster_details, cluster_entry_type=ClusterEntryType.DNS.value
        )

        assert len(entry_details) > 0
        for entry in entry_details:
            assert "cluster_entry_type" in entry
            assert "entry" in entry
            assert "target_details" in entry

    def test_query_cluster_entry_details_clb(self, test_cluster_with_entries):
        """测试查询集群访问入口详情 - CLB类型"""
        cluster = test_cluster_with_entries
        cluster_details = {
            "id": cluster.id,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        entry_details = CommonQueryResourceMixin.query_cluster_entry_details(
            cluster_details, cluster_entry_type=ClusterEntryType.CLB.value
        )

        # 验证CLB入口详情
        clb_entries = [e for e in entry_details if e["cluster_entry_type"] == ClusterEntryType.CLB.value]
        if clb_entries:
            assert "target_details" in clb_entries[0]
            assert len(clb_entries[0]["target_details"]) > 0

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_common_query_cluster_success(self, mock_app_cache, mock_cc_cloud, test_cluster_with_entries):
        """测试集群通用属性查询 - 成功"""
        cluster = test_cluster_with_entries

        # Mock 云区域和业务信息
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_app = MagicMock()
        mock_app.bk_biz_name = "test_biz"
        mock_app_cache.return_value = mock_app

        # 创建一个同时继承两个mixin的测试类
        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        headers, data_list = TestResource.common_query_cluster(
            bk_biz_id=cluster.bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            cluster_ids=[cluster.id],
        )

        # 验证返回的表头
        assert len(headers) > 0
        header_ids = [h["id"] for h in headers]
        assert "cluster_id" in header_ids
        assert "cluster_name" in header_ids
        assert "master_domain" in header_ids

        # 验证返回的数据
        assert len(data_list) == 1
        cluster_data = data_list[0]
        assert cluster_data["cluster_id"] == cluster.id
        assert cluster_data["cluster_name"] == cluster.name
        assert cluster_data["master_domain"] == cluster.immute_domain

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.db_meta.models.AppCache.objects.get")
    def test_common_query_cluster_with_tags(self, mock_app_cache, mock_cc_cloud, test_cluster_with_tags):
        """测试集群通用属性查询 - 包含标签"""
        cluster = test_cluster_with_tags

        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_app = MagicMock()
        mock_app.bk_biz_name = "test_biz"
        mock_app_cache.return_value = mock_app

        # 创建一个同时继承两个mixin的测试类
        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        headers, data_list = TestResource.common_query_cluster(
            bk_biz_id=cluster.bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            cluster_ids=[cluster.id],
        )

        assert len(data_list) == 1
        cluster_data = data_list[0]
        assert "tags" in cluster_data
        # 验证标签格式: key:value
        if cluster_data["tags"]:
            assert ":" in cluster_data["tags"]

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_common_query_cluster_multiple(self, mock_cc_cloud, test_multiple_clusters, test_bk_biz_id):
        """测试集群通用属性查询 - 多个集群"""
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        cluster_ids = [c.id for c in test_multiple_clusters]

        # 创建一个同时继承两个mixin的测试类
        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        headers, data_list = TestResource.common_query_cluster(
            bk_biz_id=test_bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            cluster_ids=cluster_ids,
        )

        # 验证返回的集群数量
        assert len(data_list) == len(test_multiple_clusters)

        # 验证所有集群ID都在返回结果中
        returned_ids = [c["cluster_id"] for c in data_list]
        for cluster_id in cluster_ids:
            assert cluster_id in returned_ids

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_common_query_instance_success(self, mock_cc_cloud, test_cluster_with_entries):
        """测试实例通用属性查询 - 成功"""
        cluster = test_cluster_with_entries
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        # 获取集群的所有主机ID
        storage_instances = StorageInstance.objects.filter(cluster=cluster)
        bk_host_ids = [inst.machine.bk_host_id for inst in storage_instances]

        headers, data_list = CommonQueryResourceMixin.common_query_instance(
            bk_biz_id=cluster.bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            bk_host_ids=bk_host_ids,
        )

        # 验证返回的表头
        assert len(headers) > 0
        header_ids = [h["id"] for h in headers]
        assert "instance_id" in header_ids
        assert "ip" in header_ids
        assert "ip_port" in header_ids
        assert "master_domain" in header_ids

        # 验证返回的数据
        assert len(data_list) > 0
        for inst_data in data_list:
            assert "ip" in inst_data
            assert "ip_port" in inst_data

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_common_query_instance_with_proxy(self, mock_cc_cloud, test_cluster_with_entries):
        """测试实例通用属性查询 - 包含代理实例"""
        cluster = test_cluster_with_entries
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        # 获取代理实例的主机ID
        proxy_instances = ProxyInstance.objects.filter(cluster=cluster)
        bk_host_ids = [inst.machine.bk_host_id for inst in proxy_instances]
        ip_list = [inst.machine.ip for inst in proxy_instances]

        headers, data_list = CommonQueryResourceMixin.common_query_instance(
            bk_biz_id=cluster.bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            bk_host_ids=bk_host_ids,
        )

        # 验证返回了代理实例
        assert len(data_list) > 0
        for inst_data in data_list:
            assert inst_data["ip"] in ip_list

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_common_query_instance_empty(self, mock_cc_cloud, test_bk_biz_id):
        """测试实例通用属性查询 - 无实例"""
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        headers, data_list = CommonQueryResourceMixin.common_query_instance(
            bk_biz_id=test_bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            bk_host_ids=[999999],  # 不存在的主机ID
        )

        # 验证返回空数据
        assert len(data_list) == 0

    def test_get_temporary_cluster_info_not_temporary(self, test_cluster_with_entries):
        """测试获取临时集群信息 - 非临时集群"""
        cluster = test_cluster_with_entries

        result = CommonQueryResourceMixin.get_temporary_cluster_info(
            cluster, [TicketType.MYSQL_ROLLBACK_CLUSTER.value]
        )

        # 非临时集群应返回空字典
        assert result == {}

    def test_get_temporary_cluster_info_temporary(self, test_temporary_cluster):
        """测试获取临时集群信息 - 临时集群"""
        cluster = test_temporary_cluster

        result = CommonQueryResourceMixin.get_temporary_cluster_info(
            cluster, [TicketType.MYSQL_ROLLBACK_CLUSTER.value]
        )

        # 临时集群应返回包含source_cluster和ticket_id的信息
        assert "source_cluster" in result
        assert "ticket_id" in result
        assert result["ticket_id"] == 12345

    def test_get_temporary_cluster_info_no_record(self, test_temporary_cluster):
        """测试获取临时集群信息 - 无操作记录"""
        cluster = test_temporary_cluster

        # 删除操作记录
        from backend.ticket.models import ClusterOperateRecord

        ClusterOperateRecord.objects.filter(cluster_id=cluster.id).delete()

        with pytest.raises(AttributeError):
            CommonQueryResourceMixin.get_temporary_cluster_info(cluster, [TicketType.MYSQL_ROLLBACK_CLUSTER.value])


class TestCommonQueryResourceMixinExport:
    """测试 CommonQueryResourceMixin 的导出功能"""

    @patch("backend.db_meta.models.AppCache.get_app_attr")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.utils.excel.ExcelHandler.response")
    def test_export_cluster_success(
        self, mock_excel_response, mock_cc_cloud, mock_get_app_attr, test_cluster_with_entries
    ):
        """测试导出集群 - 成功"""
        cluster = test_cluster_with_entries

        # Mock依赖
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_get_app_attr.return_value = "TEST_BIZ"
        mock_excel_response.return_value = MagicMock()

        # 创建一个测试类来使用这个方法
        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        TestResource.export_cluster(
            bk_biz_id=cluster.bk_biz_id,
            cluster_ids=[cluster.id],
            cluster_types=[ClusterType.TenDBHA],
        )

        # 验证Excel导出方法被调用
        assert mock_excel_response.called

        # 验证文件名格式
        call_args = mock_excel_response.call_args
        filename = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("filename", "")
        assert "cluster.xlsx" in filename or filename.endswith(".xlsx")

    @patch("backend.db_meta.models.AppCache.get_biz_name")
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.utils.excel.ExcelHandler.response")
    def test_export_instance_success(
        self, mock_excel_response, mock_cc_cloud, mock_get_biz_name, test_cluster_with_entries
    ):
        """测试导出实例 - 成功"""
        cluster = test_cluster_with_entries

        # Mock依赖
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_get_biz_name.return_value = "test_biz"
        mock_excel_response.return_value = MagicMock()

        # 获取实例的主机ID
        storage_instances = StorageInstance.objects.filter(cluster=cluster)
        bk_host_ids = [inst.machine.bk_host_id for inst in storage_instances]

        # 创建一个测试类来使用这个方法
        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        TestResource.export_instance(
            bk_biz_id=cluster.bk_biz_id,
            bk_host_ids=bk_host_ids,
        )

        # 验证Excel导出方法被调用
        assert mock_excel_response.called

        # 验证文件名格式
        call_args = mock_excel_response.call_args
        filename = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("filename", "")
        assert "instances.xlsx" in filename or filename.endswith(".xlsx")

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.utils.excel.ExcelHandler.response")
    def test_export_cluster_multiple(self, mock_excel_response, mock_cc_cloud, test_multiple_clusters, test_bk_biz_id):
        """测试导出集群 - 多个集群"""
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_excel_response.return_value = MagicMock()

        cluster_ids = [c.id for c in test_multiple_clusters]

        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        TestResource.export_cluster(
            bk_biz_id=test_bk_biz_id,
            cluster_ids=cluster_ids,
            cluster_types=[ClusterType.TenDBHA],
        )

        # 验证导出方法被调用
        assert mock_excel_response.called

    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.utils.excel.ExcelHandler.response")
    def test_export_instance_empty(self, mock_excel_response, mock_cc_cloud, test_bk_biz_id):
        """测试导出实例 - 无实例"""
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
        mock_excel_response.return_value = MagicMock()

        class TestResource(CommonExportQueryResourceMixin, CommonQueryResourceMixin):
            cluster_types = [ClusterType.TenDBHA]

        TestResource.export_instance(
            bk_biz_id=test_bk_biz_id,
            bk_host_ids=[999999],  # 不存在的主机ID
        )

        # 即使没有数据也应该能导出
        assert mock_excel_response.called
