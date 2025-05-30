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
import logging

import pytest

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, Machine, Spec, StorageInstance, StorageInstanceTuple
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.tests.mock_data.ticket.redis_flow import (
    REDIS_CLUSTER_APPLY_DATA,
    REDIS_CLUSTER_CUTOFF_DATA,
    REDIS_CLUSTER_DATA,
    REDIS_CLUSTER_DATA_COPY_DATA,
    REDIS_CLUSTER_ROLLBACK_DATA,
    REDIS_CLUSTER_SHARD_NUM_UPDATE_DATA,
    REDIS_CLUSTER_TYPE_UPDATE_DATA,
    REDIS_DATA_STRUCTURE_DATA,
    REDIS_INS_APPLY_DATA,
    REDIS_MACHINE_DATA,
    REDIS_MASTER_SLAVE_SWITCH_DATA,
    REDIS_MIGRATE_DATA,
    REDIS_PLUGIN_CREATE_CLB,
    REDIS_PROXY_SCALE_UP_DATA,
    REDIS_REBUILD_SLAVE_DATA,
    REDIS_SPEC_DATA,
    REDIS_STORAGE_INSTANCE,
    REDIS_STORAGE_INSTANCE_TUPLE,
    REDIS_STRUCTURE_TASK_DELETE_DATA,
    REDIS_TENDIS_ROLLBACK_TASK_DATA,
    REDIS_VERSION_UPDATE_DATA,
)
from backend.tests.ticket.server_base import BaseTicketTest

logger = logging.getLogger("test")
pytestmark = pytest.mark.django_db


@pytest.fixture(scope="class", autouse=True)
def setup_redis_database(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        # 初始化集群数据
        clusters = Cluster.objects.bulk_create([Cluster(**data) for data in REDIS_CLUSTER_DATA])
        Machine.objects.bulk_create([Machine(**data) for data in REDIS_MACHINE_DATA])
        storage_instances = StorageInstance.objects.bulk_create(
            [StorageInstance(**data) for data in REDIS_STORAGE_INSTANCE]
        )
        storage_instances[0].cluster.add(clusters[0])
        storage_instances[1].cluster.add(clusters[0])
        REDIS_STORAGE_INSTANCE_TUPLE["receiver"] = storage_instances[0]
        REDIS_STORAGE_INSTANCE_TUPLE["ejector"] = storage_instances[1]
        StorageInstanceTuple.objects.create(**REDIS_STORAGE_INSTANCE_TUPLE)
        Spec.objects.bulk_create([Spec(**data) for data in REDIS_SPEC_DATA])
        TbTendisRollbackTasks.objects.create(**REDIS_TENDIS_ROLLBACK_TASK_DATA)
        yield
        redis_cluster_types = ClusterType.db_type_to_cluster_types(DBType.Redis)
        Cluster.objects.filter(cluster_type__in=redis_cluster_types).delete()
        StorageInstance.objects.filter(cluster_type__in=redis_cluster_types).delete()
        Machine.objects.filter(cluster_type__in=redis_cluster_types).delete()
        StorageInstanceTuple.objects.all().delete()
        Spec.objects.filter(spec_cluster_type=DBType.Redis).delete()
        TbTendisRollbackTasks.objects.filter(temp_cluster_type__in=redis_cluster_types).delete()


class TestRedisFlow(BaseTicketTest):
    """
    redis测试类
    """

    @classmethod
    def apply_patches(cls):
        super().apply_patches()

    def test_redis_master_apply_test(self):
        # redis构建集群
        self.flow_test(REDIS_CLUSTER_APPLY_DATA)

    def test_redis_ins_apply_test(self):
        # redis构建主从集群
        self.flow_test(REDIS_INS_APPLY_DATA)

    def test_redis_data_copy_test(self):
        # redis数据复制
        self.flow_test(REDIS_CLUSTER_DATA_COPY_DATA)

    def test_redis_task_delete_test(self):
        # redis销毁构造实例
        self.flow_test(REDIS_STRUCTURE_TASK_DELETE_DATA)

    def test_redis_rebuild_slave_flow(self):
        # redis从库重建
        self.flow_test(REDIS_REBUILD_SLAVE_DATA)

    def test_redis_cut_off_flow(self):
        # redis整机替换
        self.flow_test(REDIS_CLUSTER_CUTOFF_DATA)

    def test_redis_master_slave_switch_flow(self):
        # redis主从切换
        self.flow_test(REDIS_MASTER_SLAVE_SWITCH_DATA)

    def test_redis_migrate_flow(self):
        # redis迁移
        self.flow_test(REDIS_MIGRATE_DATA)

    def test_redis_version_update(self):
        # redis版本升级
        self.flow_test(REDIS_VERSION_UPDATE_DATA)

    def test_redis_cluster_rollback_flow(self):
        # redis构造实例恢复
        self.flow_test(REDIS_CLUSTER_ROLLBACK_DATA)

    def test_redis_structure_flow(self):
        # redis集群数据构造
        self.flow_test(REDIS_DATA_STRUCTURE_DATA)

    def test_redis_proxy_scale_up_flow(self):
        # redis集群扩容
        self.flow_test(REDIS_PROXY_SCALE_UP_DATA)

    def test_redis_shard_num_update_flow(self):
        # redis集群分片变更
        self.flow_test(REDIS_CLUSTER_SHARD_NUM_UPDATE_DATA)

    def test_redis_cluster_type_update(self):
        # redis集群类型变更
        self.flow_test(REDIS_CLUSTER_TYPE_UPDATE_DATA)

    def test_redis_create_clb(self):
        # redis集群接入clb
        self.flow_test(REDIS_PLUGIN_CREATE_CLB)
