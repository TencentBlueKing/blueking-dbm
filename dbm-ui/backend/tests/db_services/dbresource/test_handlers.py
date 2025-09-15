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
from unittest.mock import patch

import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums.spec import SpecMachineType
from backend.db_meta.models import Spec, Tag
from backend.db_services.dbresource.exceptions import SpecOperateException
from backend.db_services.dbresource.handlers import (
    ClusterSpecFilter,
    MongoDBShardSpecFilter,
    RedisClusterSpecFilter,
    ResourceHandler,
    TenDBClusterSpecFilter,
    TendisCacheSpecFilter,
    TendisSSDSpecFilter,
)
from backend.tests.mock_data import constant

# SpecClusterType is actually DBType
SpecClusterType = DBType

pytestmark = pytest.mark.django_db


class TestSpecFilters:
    """测试各种规格过滤器 - 统一测试类提升覆盖率"""

    @pytest.fixture
    def mysql_specs(self):
        """创建MySQL测试规格"""
        specs = []
        for i in range(2):
            spec = Spec.objects.create(
                spec_id=1000 + i,
                spec_name=f"mysql_spec_{i}",
                spec_cluster_type=SpecClusterType.MySQL.value,
                spec_machine_type=SpecMachineType.BACKEND.value,
                cpu={"max": 16, "min": 16},
                mem={"max": 64, "min": 64},
                storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
                qps={"min": 1000, "max": 5000},
                device_class=["S5"],
                enable=True,
            )
            specs.append(spec)
        yield specs
        for spec in specs:
            spec.delete()

    @pytest.fixture
    def tendb_cluster_specs(self):
        """创建TenDBCluster测试规格"""
        specs = []
        for i in range(2):
            spec = Spec.objects.create(
                spec_id=2000 + i,
                spec_name=f"tendb_spec_{i}",
                spec_cluster_type=SpecClusterType.TenDBCluster.value,
                spec_machine_type=SpecMachineType.BACKEND.value,
                cpu={"max": 8, "min": 8},
                mem={"max": 32, "min": 32},
                storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
                qps={"min": 500 * (i + 1), "max": 2000 * (i + 1)},
                device_class=["S5"],
                enable=True,
            )
            specs.append(spec)
        yield specs
        for spec in specs:
            spec.delete()

    @pytest.fixture
    def redis_specs(self):
        """创建Redis测试规格"""
        specs = []
        for i in range(2):
            spec = Spec.objects.create(
                spec_id=3000 + i,
                spec_name=f"redis_spec_{i}",
                spec_cluster_type=SpecClusterType.Redis.value,
                spec_machine_type=SpecMachineType.TendisTwemproxyRedisInstance.value,
                cpu={"max": 4, "min": 4},
                mem={"max": 16 * (i + 1), "min": 16 * (i + 1)},
                storage_spec=[{"min": 50, "max": 200, "type": "ALL", "mount_point": "/data"}],
                device_class=["S5"],
                enable=True,
            )
            specs.append(spec)
        yield specs
        for spec in specs:
            spec.delete()

    @pytest.fixture
    def mongodb_specs(self):
        """创建MongoDB测试规格"""
        specs = []
        for i in range(2):
            spec = Spec.objects.create(
                spec_id=4000 + i,
                spec_name=f"mongodb_spec_{i}",
                spec_cluster_type=SpecClusterType.MongoDB.value,
                spec_machine_type=SpecMachineType.MONGODB.value,
                cpu={"max": 8 * (i + 1), "min": 8 * (i + 1)},
                mem={"max": 32 * (i + 1), "min": 32 * (i + 1)},
                storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
                device_class=["S5"],
                enable=True,
            )
            specs.append(spec)
        yield specs
        for spec in specs:
            spec.delete()

    def test_cluster_spec_filter_basic(self, mysql_specs):
        """测试基础的ClusterSpecFilter功能"""
        spec = mysql_specs[0]
        filter_obj = ClusterSpecFilter(
            capacity=int(spec.capacity * 2),
            future_capacity=int(spec.capacity * 3),
            spec_cluster_type=SpecClusterType.MySQL.value,
            spec_machine_type=SpecMachineType.BACKEND.value,
            qps={"min": 2000, "max": 8000},
        )

        # 测试calc_machine_pair
        filter_obj.calc_machine_pair()
        assert all(spec_data["machine_pair"] > 0 for spec_data in filter_obj.specs)
        assert all("cluster_capacity" in spec_data for spec_data in filter_obj.specs)
        assert all("cluster_qps" in spec_data for spec_data in filter_obj.specs if spec_data.get("qps"))

        # 测试QPS检查
        assert filter_obj._qps_check({"min": 1000, "max": 3000}, {"min": 2000, "max": 5000}) is True
        assert filter_obj._qps_check({"min": 1000, "max": 2000}, {"min": 3000, "max": 5000}) is False

        # 注意: ClusterSpecFilter.get_target_specs会调用calc_cluster_shard_num抽象方法
        # 这里只测试calc_machine_pair即可,不调用get_target_specs

    def test_tendb_cluster_spec_filter(self, tendb_cluster_specs):
        """测试TenDBCluster规格过滤器 - 包含分片数计算和2的幂次验证"""
        spec = tendb_cluster_specs[0]
        filter_obj = TenDBClusterSpecFilter(
            capacity=spec.capacity,
            future_capacity=spec.capacity * 3,
            spec_cluster_type=SpecClusterType.TenDBCluster.value,
            spec_machine_type=SpecMachineType.BACKEND.value,
        )

        filter_obj.calc_machine_pair()
        filter_obj.calc_cluster_shard_num()

        # 验证分片数是机器组数的整数倍
        for spec_data in filter_obj.specs:
            assert spec_data["cluster_shard_num"] % spec_data["machine_pair"] == 0

        # 测试custom_filter - 验证2的幂次
        filter_obj.custom_filter()
        for spec_data in filter_obj.specs:
            shard_num = spec_data["cluster_shard_num"]
            assert shard_num & (shard_num - 1) == 0  # 2的幂次特征

    def test_redis_spec_filters(self, redis_specs):
        """测试Redis系列规格过滤器 - TendisCache/TendisSSD/RedisCluster"""
        spec = redis_specs[0]

        # 测试TendisCacheSpecFilter
        cache_filter = TendisCacheSpecFilter(
            capacity=spec.capacity,
            future_capacity=spec.capacity * 2,
            spec_cluster_type=SpecClusterType.Redis.value,
            spec_machine_type=SpecMachineType.TendisTwemproxyRedisInstance.value,
        )
        cache_filter.calc_machine_pair()
        cache_filter.calc_cluster_shard_num()
        assert all(spec_data["cluster_shard_num"] >= 4 for spec_data in cache_filter.specs)

        # 测试TendisSSDSpecFilter
        ssd_spec = Spec.objects.create(
            spec_id=3100,
            spec_name="ssd_spec",
            spec_cluster_type=SpecClusterType.Redis.value,
            spec_machine_type=SpecMachineType.TwemproxyTendisSSDInstance.value,
            cpu={"max": 8, "min": 8},
            mem={"max": 32, "min": 32},
            storage_spec=[{"min": 200, "max": 1000, "type": "SSD", "mount_point": "/data"}],
            device_class=["S5"],
            enable=True,
        )
        ssd_filter = TendisSSDSpecFilter(
            capacity=ssd_spec.capacity,
            future_capacity=ssd_spec.capacity * 2,
            spec_cluster_type=SpecClusterType.Redis.value,
            spec_machine_type=SpecMachineType.TwemproxyTendisSSDInstance.value,
        )
        ssd_filter.calc_machine_pair()
        ssd_filter.calc_cluster_shard_num()
        for spec_data in ssd_filter.specs:
            single_shard = spec_data["cluster_shard_num"] // spec_data["machine_pair"]
            assert single_shard >= 2 and single_shard % 2 == 0

        # 测试RedisClusterSpecFilter
        cluster_filter = RedisClusterSpecFilter(
            capacity=20,
            future_capacity=40,
            spec_cluster_type=SpecClusterType.Redis.value,
            spec_machine_type=SpecMachineType.TendisTwemproxyRedisInstance.value,
        )
        cluster_filter.calc_machine_pair()
        cluster_filter.calc_cluster_shard_num()
        assert all(spec_data["machine_pair"] >= 3 for spec_data in cluster_filter.specs)

        ssd_spec.delete()

    def test_mongodb_shard_spec_filter(self, mongodb_specs):
        """测试MongoDB分片规格过滤器"""
        # 测试正常初始化
        filter_obj = MongoDBShardSpecFilter(
            capacity=100,
            spec_cluster_type=SpecClusterType.MongoDB.value,
            spec_machine_type=SpecMachineType.MONGODB.value,
        )
        assert len(filter_obj.specs) >= 2

        # 测试错误的集群类型
        with pytest.raises(SpecOperateException):
            MongoDBShardSpecFilter(
                capacity=100,
                spec_cluster_type=SpecClusterType.MySQL.value,
                spec_machine_type=SpecMachineType.MONGODB.value,
            )

        # 测试get_shard_spec
        spec_dict = {"cpu": {"min": 8}, "mem": {"min": 32}, "capacity": 100, "machine_pair": 2}
        shard_spec = MongoDBShardSpecFilter.get_shard_spec(spec_dict, 4)
        assert "4核" in shard_spec
        assert "16G内存" in shard_spec
        assert "50G容量" in shard_spec

        # 测试get_target_specs
        result = filter_obj.get_target_specs()
        assert isinstance(result, list)
        for spec in result:
            assert "shard_choices" in spec
            assert "shard_recommend" in spec


class TestResourceHandler:
    """测试ResourceHandler类 - 统一测试资源处理功能"""

    @pytest.fixture
    def test_specs(self):
        """创建测试规格"""
        specs = []
        for i in range(2):
            spec = Spec.objects.create(
                spec_id=5000 + i,
                spec_name=f"resource_spec_{i}",
                spec_cluster_type=SpecClusterType.MySQL.value,
                spec_machine_type=SpecMachineType.BACKEND.value,
                cpu={"max": 8, "min": 8},
                mem={"max": 32, "min": 32},
                storage_spec=[{"min": 100, "max": 500, "type": "ALL", "mount_point": "/data"}],
                device_class=["S5"],
                enable=True,
            )
            specs.append(spec)
        yield specs
        for spec in specs:
            spec.delete()

    @patch("backend.db_services.dbresource.handlers.DBResourceApi.apply_count")
    def test_spec_resource_count(self, mock_apply_count, test_specs):
        """测试规格预估资源数量 - 包含成功和异常情况"""
        spec_ids = [spec.spec_id for spec in test_specs]
        mock_apply_count.return_value = {"5000": 10, "5001": 8}

        # 测试成功场景
        result = ResourceHandler.spec_resource_count(
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=0,
            sub_zone_ids=[1],
            spec_ids=spec_ids,
            city="shanghai",
        )
        assert mock_apply_count.called
        assert isinstance(result, dict)

        # 测试空规格列表
        result = ResourceHandler.spec_resource_count(
            bk_biz_id=constant.BK_BIZ_ID,
            bk_cloud_id=0,
            sub_zone_ids=[1],
            spec_ids=[99999],
            city="shanghai",
        )
        assert result == {}

        # 测试混合集群类型抛出异常
        redis_spec = Spec.objects.create(
            spec_id=5100,
            spec_name="redis_spec",
            spec_cluster_type=SpecClusterType.Redis.value,
            spec_machine_type=SpecMachineType.TendisTwemproxyRedisInstance.value,
            cpu={"max": 4, "min": 4},
            mem={"max": 16, "min": 16},
            storage_spec=[{"min": 50, "max": 200, "type": "ALL", "mount_point": "/data"}],
            device_class=["S5"],
            enable=True,
        )
        with pytest.raises(SpecOperateException):
            ResourceHandler.spec_resource_count(
                bk_biz_id=constant.BK_BIZ_ID,
                bk_cloud_id=0,
                sub_zone_ids=[1],
                spec_ids=[test_specs[0].spec_id, redis_spec.spec_id],
                city="shanghai",
            )
        redis_spec.delete()

    @patch("backend.db_services.dbresource.handlers.DBResourceApi.resource_list")
    @patch("backend.db_services.dbresource.handlers.ResourceQueryHelper.search_cc_cloud")
    @patch("backend.db_services.dbresource.handlers.AppCache.batch_get_app_attr")
    def test_resource_list(self, mock_batch_get, mock_search_cloud, mock_resource_list):
        """测试资源列表 - 包含空列表和带数据两种情况"""
        # 测试空列表
        mock_resource_list.return_value = {"details": []}
        mock_search_cloud.return_value = {"0": {"bk_cloud_name": "Default"}}
        result = ResourceHandler.resource_list({})
        assert result["count"] == 0
        assert result["results"] == []

        # 测试包含数据
        tag = Tag.objects.create(key="env", value="test")
        mock_resource_list.return_value = {
            "count": 1,
            "details": [
                {
                    "ip": "1.1.1.1",
                    "bk_cloud_id": 0,
                    "dram_cap": 32,
                    "cpu_num": 8,
                    "total_storage_cap": 500,
                    "rs_type": "mysql",
                    "dedicated_biz": constant.BK_BIZ_ID,
                    "gse_agent_status_code": 0,
                    "labels": [str(tag.id)],
                }
            ],
        }
        mock_batch_get.return_value = {constant.BK_BIZ_ID: "test_biz"}

        result = ResourceHandler.resource_list({})
        assert result["count"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["ip"] == "1.1.1.1"
        assert result["results"][0]["bk_mem"] == 32
        assert result["results"][0]["bk_cpu"] == 8

        tag.delete()

    @patch("backend.db_services.dbresource.handlers.SystemSettings.get_setting_value")
    def test_spec_cost_estimate(self, mock_get_setting, test_specs):
        """测试规格预估运营成本"""
        mock_get_setting.return_value = {DBType.MySQL: {"cpu": 10, "mem": 5, "storage": {"ALL": 2, "SSD": 3}}}

        resource_spec = {
            "backend_group": {"spec_id": test_specs[0].spec_id, "count": 2},
            "proxy": {"spec_id": test_specs[1].spec_id, "count": 1},
        }

        result = ResourceHandler.spec_cost_estimate(DBType.MySQL, resource_spec)
        assert isinstance(result, int)
        assert result > 0

    @patch("backend.db_services.dbresource.handlers.ResourceQueryHelper.search_cc_hosts")
    @patch("backend.db_services.dbresource.handlers.CCApi.batch_find_host_biz_relations")
    def test_standardized_resource_host(self, mock_batch_find, mock_search_hosts):
        """测试标准化主机信息"""
        mock_search_hosts.return_value = [
            {
                "bk_host_id": 1,
                "bk_host_innerip": "1.1.1.1",
                "bk_cpu": 8,
                "bk_mem": 32,
                "bk_disk": 500,
                "idc_city_name": "shanghai",
                "bk_os_name": "CentOS",
                "bk_os_type": "Linux",
                "svr_device_class": "S5",
            }
        ]
        mock_batch_find.return_value = [{"bk_host_id": 1, "bk_biz_id": constant.BK_BIZ_ID}]

        hosts = [{"bk_host_id": 1}]
        result = ResourceHandler.standardized_resource_host(hosts)

        assert len(result) == 1
        assert result[0]["bk_host_id"] == 1
        assert result[0]["ip"] == "1.1.1.1"
        assert result[0]["bk_biz_id"] == constant.BK_BIZ_ID
        assert result[0]["city"] == "shanghai"
