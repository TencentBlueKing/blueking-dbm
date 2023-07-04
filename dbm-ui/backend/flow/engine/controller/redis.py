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
from backend.flow.engine.bamboo.scene.redis.redis_add_dts_server import RedisAddDtsServerFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_apply_flow import RedisClusterApplyFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_backup import RedisClusterBackupFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_dts import RedisClusterDtsFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_open_close import RedisClusterOpenCloseFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_cmr import RedisClusterCMRSceneFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_shutdown import RedisClusterShutdownFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.engine.bamboo.scene.redis.redis_dbmon import RedisDbmonSceneFlow
from backend.flow.engine.bamboo.scene.redis.redis_flush_data import RedisFlushDataFlow
from backend.flow.engine.bamboo.scene.redis.redis_keys_delete import RedisKeysDeleteFlow
from backend.flow.engine.bamboo.scene.redis.redis_keys_extract import RedisKeysExtractFlow
from backend.flow.engine.bamboo.scene.redis.redis_proxy_scale import RedisProxyScaleFlow
from backend.flow.engine.bamboo.scene.redis.redis_remove_dts_server import RedisRemoveDtsServerFlow
from backend.flow.engine.bamboo.scene.redis.singele_redis_shutdown import SingleRedisShutdownFlow
from backend.flow.engine.bamboo.scene.redis.single_proxy_shutdown import SingleProxyShutdownFlow
from backend.flow.engine.bamboo.scene.redis.tendis_plus_apply_flow import TendisPlusApplyFlow
from backend.flow.engine.controller.base import BaseController


class RedisController(BaseController):
    """
    redis实例相关调用
    """

    def redis_cluster_apply_scene(self):
        """
        redis集群部署场景
        """
        flow = RedisClusterApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_redis_cluster_flow()

    def tendisplus_apply_scene(self):
        """
        redis集群部署场景
        """
        flow = TendisPlusApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_tendisplus_cluster_flow()

    def redis_keys_extract(self):
        """
        redis提取key场景
        """
        flow = RedisKeysExtractFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_keys_extract_flow()

    def redis_keys_delete(self):
        """
        redis删除keys
        """
        flow = RedisKeysDeleteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_keys_delete_flow()

    def redis_backup(self):
        """
        redis备份
        """
        flow = RedisClusterBackupFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_backup_flow()

    def redis_cluster_open_close_scene(self):
        """
        redis集群启停
        """
        flow = RedisClusterOpenCloseFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_open_close_flow()

    def redis_cluster_shutdown(self):
        """
        redis集群下架
        """
        flow = RedisClusterShutdownFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_shutdown_flow()

    def single_redis_shutdown(self):
        """
        孤立redis节点下架
        """
        flow = SingleRedisShutdownFlow(root_id=self.root_id, data=self.ticket_data)
        flow.single_redis_shutdown_flow()

    def single_proxy_shutdown(self):
        """
        孤立proxy节点下架
        """
        flow = SingleProxyShutdownFlow(root_id=self.root_id, data=self.ticket_data)
        flow.single_proxy_shutdown_flow()

    def redis_flush_data(self):
        """
        redis集群清档
        """
        flow = RedisFlushDataFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_flush_data_flow()

    def redis_proxy_scale(self):
        """
        proxy 新增、删除
        """
        flow = RedisProxyScaleFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_proxy_scale_flow()

    def redis_cluster_cutoff_scene(self):
        """
        tendis 集群版, master/slave/proxy 裁撤、迁移场景
        """
        flow = RedisClusterCMRSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.complete_machine_replace()

    def redis_install_dbmon_scene(self):
        """
        tendis 安装dbmon, 适用于 proxy、 redis
        """
        flow = RedisDbmonSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.batch_update_dbmon()

    def redis_dts(self):
        """
        redis 数据迁移
        """
        flow = RedisClusterDtsFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_dts_flow()

    def redis_add_dts_server(self):
        """
        redis add dts server
        """
        flow = RedisAddDtsServerFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_add_dts_server_flow()

    def redis_remove_dts_server(self):
        """
        redis remove dts server
        """
        flow = RedisRemoveDtsServerFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_remove_dts_server_flow()

    def redis_data_structure(self):
        """
        redis 数据构造
        """
        flow = RedisDataStructureFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_data_structure_flow()

    def redis_data_structure_task_delete(self):
        """
        redis 数据构造
        """
        flow = RedisDataStructureTaskDeleteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_rollback_task_delete_flow()
