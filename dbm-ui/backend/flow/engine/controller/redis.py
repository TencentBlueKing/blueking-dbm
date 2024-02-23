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
from backend.flow.engine.bamboo.scene.redis.redis_backend_scale import RedisBackendScaleFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_add_slave import RedisClusterAddSlaveFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_backup import RedisClusterBackupFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_data_check_repair import RedisClusterDataCheckRepairFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_data_copy import RedisClusterDataCopyFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_instance_shutdown import (
    RedisClusterInstanceShutdownSceneFlow,
)
from backend.flow.engine.bamboo.scene.redis.redis_cluster_migrate_compair import RedisClusterMigrateCompairFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_migrate_load import RedisClusterMigrateLoadFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_migrate_precheck import RedisClusterMigratePrecheckFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_open_close import RedisClusterOpenCloseFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_auotfix import RedisClusterAutoFixSceneFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_cmr import RedisClusterCMRSceneFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_scene_mss import RedisClusterMSSSceneFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_shutdown import RedisClusterShutdownFlow
from backend.flow.engine.bamboo.scene.redis.redis_cluster_version_update_online import RedisClusterVersionUpdateOnline
from backend.flow.engine.bamboo.scene.redis.redis_data_structure import RedisDataStructureFlow
from backend.flow.engine.bamboo.scene.redis.redis_data_structure_task_delete import RedisDataStructureTaskDeleteFlow
from backend.flow.engine.bamboo.scene.redis.redis_dbmon import RedisDbmonSceneFlow
from backend.flow.engine.bamboo.scene.redis.redis_flush_data import RedisFlushDataFlow
from backend.flow.engine.bamboo.scene.redis.redis_instance_apply_flow import RedisInstanceApplyFlow
from backend.flow.engine.bamboo.scene.redis.redis_keys_delete import RedisKeysDeleteFlow
from backend.flow.engine.bamboo.scene.redis.redis_keys_extract import RedisKeysExtractFlow
from backend.flow.engine.bamboo.scene.redis.redis_predixy_config_servers_rewrite import (
    RedisPredixyConfigServersRewriteFlow,
)
from backend.flow.engine.bamboo.scene.redis.redis_predixy_cluster_apply_flow import TendisPlusApplyFlow
from backend.flow.engine.bamboo.scene.redis.redis_proxy_scale import RedisProxyScaleFlow
from backend.flow.engine.bamboo.scene.redis.redis_remove_dts_server import RedisRemoveDtsServerFlow
from backend.flow.engine.bamboo.scene.redis.redis_reupload_old_backup_records import RedisReuploadOldBackupRecordsFlow
from backend.flow.engine.bamboo.scene.redis.redis_slots_migrate import RedisSlotsMigrateFlow
from backend.flow.engine.bamboo.scene.redis.redis_twemproxy_cluster_apply_flow import RedisClusterApplyFlow
from backend.flow.engine.bamboo.scene.redis.singele_redis_shutdown import SingleRedisShutdownFlow
from backend.flow.engine.bamboo.scene.redis.single_proxy_shutdown import SingleProxyShutdownFlow
from backend.flow.engine.controller.base import BaseController


class RedisController(BaseController):
    """
    redis实例相关调用
    """

    def twemproxy_cluster_apply_scene(self):
        """
        redis twemproxy集群部署场景
        """
        flow = RedisClusterApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_twemproxy_cluster_flow()

    def predixy_cluster_apply_scene(self):
        """
        redis cluster + predixy 集群部署场景
        """
        flow = TendisPlusApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_predixy_cluster_flow()

    def redis_instance_apply_scene(self):
        """
        redis 主从部署场景
        """
        flow = RedisInstanceApplyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.deploy_redis_instance_flow()

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

    def redis_backend_scale(self):
        """
        redis后端扩缩容
        """
        flow = RedisBackendScaleFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_backend_scale_flow()

    def redis_cluster_cutoff_scene(self):
        """
        tendis 集群版, master/slave/proxy 裁撤、迁移场景
        """
        flow = RedisClusterCMRSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.complete_machine_replace()

    def redis_cluster_auotfix_scene(self):
        """
        tendis 集群版, slave/proxy 故障自愈
        """
        flow = RedisClusterAutoFixSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.start_redis_auotfix()

    def redis_cluster_instance_shutdown(self):
        """
        提交实例下架单据
        """
        flow = RedisClusterInstanceShutdownSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.start_instance_shutdown()

    def redis_cluster_failover_scene(self):
        """
        tendis 集群版, master slave 故障切换
        """
        flow = RedisClusterMSSSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_ms_switch()

    def redis_install_dbmon_scene(self):
        """
        tendis 安装dbmon, 适用于 proxy、 redis
        """
        flow = RedisDbmonSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.batch_ips_update_dbmon()

    def redis_clusters_reinstall_dbmon_scene(self):
        """
        tendis 集群重新安装dbmon, 集群所有proxy、 redis机器dbmon都会被重装
        """
        flow = RedisDbmonSceneFlow(root_id=self.root_id, data=self.ticket_data)
        flow.batch_clusters_update_dbmon()

    def redis_cluster_data_copy(self):
        """
        redis 数据复制
        """
        flow = RedisClusterDataCopyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_data_copy_flow()

    def redis_cluster_shard_num_update(self):
        """
        redis 集群分片变更
        """
        flow = RedisClusterDataCopyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shard_num_or_cluster_type_update_flow()

    def redis_cluster_type_update(self):
        """
        redis 集群类型变更
        """
        flow = RedisClusterDataCopyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.shard_num_or_cluster_type_update_flow()

    def redis_dts_online_switch(self):
        """
        redis  dts在线切换
        """
        flow = RedisClusterDataCopyFlow(root_id=self.root_id, data=self.ticket_data)
        flow.online_switch_flow()

    def redis_cluster_data_check_repair(self):
        """
        redis 数据校验与修复
        """
        flow = RedisClusterDataCheckRepairFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_data_check_repair_flow()

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

    def redis_cluster_add_slave(self):
        """
        redis 新建从库
        """
        flow = RedisClusterAddSlaveFlow(root_id=self.root_id, data=self.ticket_data)
        flow.add_slave_flow()

    def redis_cluster_migrate_precheck(self):
        """
        redis迁移前置检查
        """
        flow = RedisClusterMigratePrecheckFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_migrate_precheck_flow()

    def redis_cluster_migrate_load(self):
        """
        redis迁移
        """
        flow = RedisClusterMigrateLoadFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_migrate_load_flow()

    def redis_cluster_migrate_compair(self):
        """
        redis迁移后置验证
        """
        flow = RedisClusterMigrateCompairFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_cluster_migrate_compair()

    def redis_cluster_version_update_online(self):
        """
        redis 集群版本在线升级
        """
        flow = RedisClusterVersionUpdateOnline(root_id=self.root_id, data=self.ticket_data)
        flow.version_update_flow()

    def redis_slots_migrate_for_expansion(self):
        """
        redis slots migrate for 扩容
        """
        flow = RedisSlotsMigrateFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_migrate_4_expansion_flow()

    def redis_slots_migrate_for_contraction(self):
        """
        redis slots migrate for 缩容
        """
        flow = RedisSlotsMigrateFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_migrate_4_contraction_flow()

    def redis_slots_migrate_for_hotkey(self):
        """
        redis slots migrate for 热点key
        """
        flow = RedisSlotsMigrateFlow(root_id=self.root_id, data=self.ticket_data)
        flow.redis_slots_migrate_for_hotkey_flow()

    def redis_reupload_old_backup_records(self):
        """
        redis 重新上报备份记录
        """
        flow = RedisReuploadOldBackupRecordsFlow(root_id=self.root_id, data=self.ticket_data)
        flow.reupload_old_backup_records_flow()

    def redis_predixy_config_servers_rewrite_scene(self):
        """
        tendis 集群Predixy配置文件servers rewrite
        """
        flow = RedisPredixyConfigServersRewriteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.batch_clusters_predixy_config_servers_rewrite()
