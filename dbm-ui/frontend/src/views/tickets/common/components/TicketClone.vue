<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div v-show="isShowTicketClone">
    <BkButton
      class="mr-8"
      disabled
      theme="primary"
      @click="handleCancelTicket">
      {{ t('撤销单据') }}
    </BkButton>
    <BkButton @click="handleResubmitTicket">
      {{ t('再次提单') }}
    </BkButton>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  interface Props {
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const ticketTypeRouteNameMap: Record<string, string> = {
    [TicketTypes.REDIS_CLUSTER_APPLY]: 'SelfServiceApplyRedis', // Redis 申请部署
    [TicketTypes.REDIS_CLUSTER_CUTOFF]: 'RedisDBReplace', // Redis 整机替换
    [TicketTypes.REDIS_PROXY_SCALE_UP]: 'RedisProxyScaleUp', // Redis 扩容接入层
    [TicketTypes.REDIS_PROXY_SCALE_DOWN]: 'RedisProxyScaleDown', // Redis 缩容接入层
    [TicketTypes.REDIS_SCALE_UPDOWN]: 'RedisCapacityChange', // Redis 集群容量变更
    [TicketTypes.REDIS_MASTER_SLAVE_SWITCH]: 'RedisMasterFailover', // Redis 主从切换
    [TicketTypes.REDIS_DATA_STRUCTURE]: 'RedisDBStructure', // Redis 定点构造
    [TicketTypes.REDIS_CLUSTER_ADD_SLAVE]: 'RedisDBCreateSlave', // Redis 重建从库
    [TicketTypes.REDIS_CLUSTER_DATA_COPY]: 'RedisDBDataCopy', // Redis 数据复制
    [TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE]: 'RedisClusterShardUpdate', // Redis 集群分片变更
    [TicketTypes.REDIS_CLUSTER_TYPE_UPDATE]: 'RedisClusterTypeUpdate', // Redis 集群类型变更
    [TicketTypes.REDIS_DATACOPY_CHECK_REPAIR]: 'RedisToolboxDataCheckRepair', // Redis 数据校验修复
    [TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY]: 'RedisRecoverFromInstance', // Redis 以构造实例恢复
    [TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE]: 'RedisStructureInstance', // Redis 删除构造任务
    [TicketTypes.REDIS_KEYS_EXTRACT]: 'DatabaseRedisList', // Redis 提取 Key
    [TicketTypes.REDIS_KEYS_DELETE]: 'DatabaseRedisList', // Redis 删除 key
    [TicketTypes.REDIS_BACKUP]: 'DatabaseRedisList', // Redis 集群备份
    [TicketTypes.REDIS_PURGE]: 'DatabaseRedisList', // Redis 集群清档
    [TicketTypes.REDIS_PROXY_CLOSE]: 'DatabaseRedisList', // Redis 集群禁用
    [TicketTypes.REDIS_PROXY_OPEN]: 'DatabaseRedisList', // Redis 集群启用
    [TicketTypes.REDIS_DESTROY]: 'DatabaseRedisList', // Redis 集群删除
    [TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB]: 'DatabaseRedisList', // Redis 绑定CLB
    [TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB]: 'DatabaseRedisList', // Redis 解绑CLB
    [TicketTypes.REDIS_PLUGIN_CREATE_CLB]: 'DatabaseRedisList', // Redis 创建CLB
    [TicketTypes.REDIS_PLUGIN_DELETE_CLB]: 'DatabaseRedisList', // Redis 删除CLB
    [TicketTypes.REDIS_PLUGIN_CREATE_POLARIS]: 'DatabaseRedisList', // Redis 删除构造任务
    [TicketTypes.REDIS_PLUGIN_DELETE_POLARIS]: 'DatabaseRedisList', // Redis 删除构造任务
    [TicketTypes.MYSQL_SINGLE_APPLY]: 'SelfServiceApplySingle', // Mysql 单节点部署
    [TicketTypes.MYSQL_HA_APPLY]: 'SelfServiceApplyHa', // Mysql 主从部署
    [TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES]: '', // Mysql excel 授权
    [TicketTypes.MYSQL_AUTHORIZE_RULES]: 'PermissionRules', // Mysql 授权
    [TicketTypes.MYSQL_HA_DISABLE]: 'DatabaseTendbha', // Mysql 禁用
    [TicketTypes.MYSQL_HA_ENABLE]: 'DatabaseTendbha', // Mysql 启用
    [TicketTypes.MYSQL_HA_DESTROY]: 'DatabaseTendbha', // Mysql 删除
    [TicketTypes.MYSQL_SINGLE_DISABLE]: 'DatabaseTendbsingle', // Mysql 单节点禁用
    [TicketTypes.MYSQL_SINGLE_ENABLE]: 'DatabaseTendbsingle', // Mysql 单节点启用
    [TicketTypes.MYSQL_SINGLE_DESTROY]: 'DatabaseTendbsingle', // Mysql 单节点删除
    [TicketTypes.MYSQL_INSTANCE_CLONE_RULES]: 'MySQLPrivilegeCloneInst', // Mysql DB实例权限克隆
    [TicketTypes.MYSQL_CLIENT_CLONE_RULES]: 'MySQLPrivilegeCloneClient', // Mysql 客户端权限克隆
    [TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE]: 'MySQLSlaveRebuild', // Mysql 重建从库
    [TicketTypes.MYSQL_HA_RENAME_DATABASE]: 'MySQLDBRename', // Mysql DB重命名
    [TicketTypes.MYSQL_SINGLE_RENAME_DATABASE]: 'MySQLDBRename', // Mysql DB重命名
    [TicketTypes.MYSQL_ADD_SLAVE]: 'MySQLSlaveAdd', // Mysql 添加从库
    [TicketTypes.MYSQL_HA_TRUNCATE_DATA]: 'MySQLDBClear', // Mysql 高可用清档
    [TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA]: 'MySQLDBClear', // Mysql 单节点清档
    [TicketTypes.MYSQL_CHECKSUM]: 'MySQLChecksum', // Mysql 数据校验修复
    [TicketTypes.MYSQL_PROXY_SWITCH]: 'MySQLProxyReplace', // Mysql 替换Proxy
    [TicketTypes.MYSQL_HA_DB_TABLE_BACKUP]: 'MySQLDBTableBackup', // Mysql 库表备份
    [TicketTypes.MYSQL_MIGRATE_CLUSTER]: 'MySQLMasterSlaveClone', // Mysql 迁移主从
    [TicketTypes.MYSQL_MASTER_SLAVE_SWITCH]: 'MySQLMasterSlaveSwap', // Mysql 主从互切
    [TicketTypes.MYSQL_PROXY_ADD]: 'MySQLProxyAdd', // Mysql 添加Proxy
    [TicketTypes.MYSQL_MASTER_FAIL_OVER]: 'MySQLMasterFailover', // Mysql 主库故障切换
    [TicketTypes.MYSQL_IMPORT_SQLFILE]: 'MySQLExecute', // Mysql 变更SQL执行
    [TicketTypes.MYSQL_FLASHBACK]: 'MySQLDBFlashback', // Mysql 闪回
    [TicketTypes.MYSQL_ROLLBACK_CLUSTER]: 'MySQLDBRollback', // Mysql 定点构造
    [TicketTypes.MYSQL_RESTORE_SLAVE]: 'MySQLSlaveRebuild', // Mysql 重建从库
    [TicketTypes.MYSQL_HA_FULL_BACKUP]: 'MySQLDBBackup', // Mysql 全库备份
    [TicketTypes.MYSQL_OPEN_AREA]: 'MySQLOpenareaTemplate', // Mysql 新建开区
    [TicketTypes.MYSQL_DATA_MIGRATE]: 'MySQLDataMigrate', // Mysql DB克隆
    [TicketTypes.MYSQL_PROXY_UPGRADE]: 'MySQLVersionUpgrade', // MySQL Proxy 升级
    [TicketTypes.MYSQL_LOCAL_UPGRADE]: 'MySQLVersionUpgrade', // MySQL 原地升级
    [TicketTypes.MYSQL_MIGRATE_UPGRADE]: 'MySQLVersionUpgrade', // MySQL 迁移升级
    [TicketTypes.TENDBCLUSTER_OPEN_AREA]: 'spiderOpenareaTemplate', // Spider 开区
    [TicketTypes.REDIS_VERSION_UPDATE_ONLINE]: 'RedisVersionUpgrade', // redis 版本升级
    [TicketTypes.SQLSERVER_DATA_MIGRATE]: 'sqlServerDataMigrate', // sqlserver 数据迁移
    [TicketTypes.SQLSERVER_CLEAR_DBS]: 'sqlServerDBClear', // sqlserver 清档
    [TicketTypes.SQLSERVER_DBRENAME]: 'sqlServerDBRename', // sqlserver DB重命名
    [TicketTypes.SQLSERVER_BACKUP_DBS]: 'SqlServerDbBackup', // sqlserver 库备份
    [TicketTypes.SQLSERVER_MASTER_FAIL_OVER]: 'sqlServerMasterFailover', // sqlserver 主库故障切换
    [TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH]: 'sqlServerMasterSlaveSwap', // sqlserver 主从互切
    [TicketTypes.SQLSERVER_ROLLBACK]: 'sqlServerDBRollback', // sqlserver 定点构造
    [TicketTypes.SQLSERVER_ADD_SLAVE]: 'sqlServerSlaveAdd', // sqlserver 添加从库
    [TicketTypes.SQLSERVER_RESTORE_SLAVE]: 'sqlServerSlaveRebuild', // sqlserver 重建从库_新机重建
    [TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE]: 'sqlServerSlaveRebuild', // sqlserver 重建从库_原地重建
    [TicketTypes.SQLSERVER_IMPORT_SQLFILE]: 'sqlServerExecute', // sqlserver 变更SQL执行
    [TicketTypes.SQLSERVER_FULL_MIGRATE]: 'sqlServerDataMigrate', // sqlserver 全库迁移
    [TicketTypes.SQLSERVER_INCR_MIGRATE]: 'sqlServerDataMigrate', // sqlserver 增量迁移
    [TicketTypes.TENDBCLUSTER_APPLY]: 'spiderApply', // spider 集群部署
    [TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES]: 'SpiderProxyScaleUp', // Spider扩容接入层
    [TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES]: 'SpiderProxyScaleDown', // Spider缩容接入层
    [TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY]: 'SpiderProxySlaveApply', // Spider 部署只读接入层
    [TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY]: 'spiderAddMnt', // Spider 添加运维节点
    [TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH]: 'spiderMasterSlaveSwap', // Spider remote 主从切换
    [TicketTypes.TENDBCLUSTER_RENAME_DATABASE]: 'spiderDbRename', // Spider Tendbcluster 重命名
    [TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER]: 'spiderMasterFailover', // Spider remote主故障切换
    [TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP]: 'spiderDbTableBackup', // Spider TenDBCluster 库表备份
    [TicketTypes.TENDBCLUSTER_FULL_BACKUP]: 'spiderDbBackup', // Spider TenDBCluster 全备单据
    [TicketTypes.TENDBCLUSTER_NODE_REBALANCE]: 'spiderCapacityChange', // Spider 集群remote节点扩缩容
    [TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER]: 'spiderRollback', // Spider 定点回档
    [TicketTypes.TENDBCLUSTER_FLASHBACK]: 'spiderFlashback', // Spider 闪回
    [TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE]: 'spiderDbClear', // Spider tendbcluster 清档
    [TicketTypes.TENDBCLUSTER_CHECKSUM]: 'spiderChecksum', // Spider checksum
    [TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES]: 'spiderPrivilegeCloneClient', // Spider 客户端权限克隆
    [TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES]: 'spiderPrivilegeCloneInst', // Spider DB 实例权限克隆
    [TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES]: 'spiderPermission',
    [TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE]: 'spiderSqlExecute', // Spider SQL变更执行
    [TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER]: 'spiderMasterSlaveClone', // spider 迁移主从
    [TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE]: 'spiderSlaveRebuild', // spider 重建从库-原地重建
    [TicketTypes.TENDBCLUSTER_RESTORE_SLAVE]: 'spiderSlaveRebuild', // spider 重建从库-新机重建
  };

  const isShowTicketClone = computed(() => !!ticketTypeRouteNameMap[props.data.ticket_type]);

  const handleResubmitTicket = async () => {
    let name = '';
    if (
      [
        TicketTypes.REDIS_KEYS_EXTRACT,
        TicketTypes.REDIS_KEYS_DELETE,
        TicketTypes.REDIS_BACKUP,
        TicketTypes.REDIS_PURGE,
      ].includes(props.data.ticket_type)
    ) {
      const clusterInfo = Object.values((props.data.details as Redis.RedisRollbackDataCopyDetails).clusters)[0];
      if (clusterInfo.cluster_type === ClusterTypes.REDIS_INSTANCE) {
        name = 'DatabaseRedisHaList';
      } else {
        name = 'DatabaseRedisList';
      }
    } else {
      name = ticketTypeRouteNameMap[props.data.ticket_type];
    }
    if (name) {
      router.push({
        name,
        query: {
          ticketId: props.data.id,
          ticketType: props.data.ticket_type,
        },
      });
    }
  };

  const handleCancelTicket = () => {
    console.log('接口未准备好');
  };
</script>
