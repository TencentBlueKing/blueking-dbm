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
  <Component
    :is="detailsComp"
    :key="data.id"
    :ticket-details="data" />
</template>

<script setup lang="tsx">
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import DetailsClusterOperation from './bigdata/DetailsClusterOperation.vue';
  import DetailsES from './bigdata/DetailsES.vue';
  import DetailsHDFS from './bigdata/DetailsHDFS.vue';
  import DetailsInfluxDB from './bigdata/DetailsInfluxDB.vue';
  import DetailsKafka from './bigdata/DetailsKafka.vue';
  import DetailsPulsar from './bigdata/DetailsPulsar.vue';
  import BigDataExpansionCapacity from './bigdata/ExpansionCapacity.vue';
  import BigDataReboot from './bigdata/Reboot.vue';
  import BigDataReplace from './bigdata/Replace.vue';
  import InfluxdbOperations from './influxdb/Operations.vue';
  import InfluxdbReplace from './influxdb/Replace.vue';
  import MySQLChecksum from './mysql/Checksum.vue';
  import MySQLClone from './mysql/Clone.vue';
  import MySQLClusterOperation from './mysql/ClusterOperation.vue';
  import DetailsMySQL from './mysql/Details.vue';
  import MySQLFlashback from './mysql/Flashback.vue';
  import MySQLFullBackup from './mysql/FullBackup.vue';
  import MySQLHATruncate from './mysql/HATruncate.vue';
  import MySQLImportSQLFile from './mysql/ImportSQLFile.vue';
  import MySQLMasterFailOver from './mysql/MasterFailOver.vue';
  import MySQLMasterSlaveSwitch from './mysql/MasterSlaveSwitch.vue';
  import MySQLMigrateCluster from './mysql/MigrateCluster.vue';
  import MySQLOperation from './mysql/Operation.vue';
  import MySQLProxyAdd from './mysql/ProxyAdd.vue';
  import MySQLProxySwitch from './mysql/ProxySwitch.vue';
  import MySQLRename from './mysql/Rename.vue';
  import MySQLRestoreSlave from './mysql/RestoreSlave.vue';
  import MySQLRollbackCluster from './mysql/RollbackCluster.vue';
  import MySQLSlave from './mysql/Slave.vue';
  import MySQLTableBackup from './mysql/TableBackup.vue';
  import RedisAddSlave from './redis/AddSlave.vue';
  import CLBDetail from './redis/CLBDetail.vue';
  import RedisClusterCapacityUpdate from './redis/ClusterCapacityUpdate.vue';
  import RedisClusterShardUpdate from './redis/ClusterShardUpdate.vue';
  import RedisClusterTypeUpdate from './redis/ClusterTypeUpdate.vue';
  import RedisDataCheckAndRepair from './redis/DataCheckAndRepair.vue';
  import RedisDataCopy from './redis/DataCopy.vue';
  import RedisDataStructure from './redis/DataStructure.vue';
  import RedisDBReplace from './redis/DBReplace.vue';
  import DetailsRedis from './redis/Details.vue';
  import RedisMasterFailover from './redis/MasterFailover.vue';
  import RedisOperation from './redis/Operation.vue';
  import RedisProxyScaleDown from './redis/ProxyScaleDown.vue';
  import RedisProxyScaleUp from './redis/ProxyScaleUp.vue';
  import RedisRollbackDataCopy from './redis/RollbackDataCopy.vue';
  import RedisStructureDelete from './redis/StructureDelete.vue';
  import SpiderAddNodes from './spider/AddNodes.vue';
  import SpiderAuthorizeRules from './spider/AuthorizeRules.vue';
  import SpiderCheckSum from './spider/CheckSum.vue';
  import SpiderDestroy from './spider/Destroy.vue';
  import DetailsSpider from './spider/Details.vue';
  import SpiderDisable from './spider/Disable.vue';
  import SpiderEnable from './spider/Enable.vue';
  import SpiderFlashback from './spider/Flashback.vue';
  import SpiderFullBackup from './spider/FullBackup.vue';
  import SpiderMasterSlaveSwitch from './spider/MasterSlaveSwitch.vue';
  import SpiderMNTApply from './spider/MNTApply.vue';
  import SpiderMNTDestroy from './spider/MNTDestroy.vue';
  import SpiderNodeRebalance from './spider/NodeRebalance.vue';
  import SpiderPartitionManage from './spider/PartitionManage.vue';
  import SpiderReduceNodes from './spider/ReduceNodes.vue';
  import SpiderRenameDatabase from './spider/RenameDatabase.vue';
  import SpiderRollback from './spider/Rollback.vue';
  import SpiderSlaveApply from './spider/SlaveApply.vue';
  import SpiderSlaveDestroy from './spider/SlaveDestroy.vue';
  import SpiderTableBackup from './spider/TableBackup.vue';
  import SpiderTruncateDatabase from './spider/TruncateDatabase.vue';

  interface Props {
    data: TicketModel
  }

  const props = defineProps<Props>();

  const redisKeysType = [
    TicketTypes.REDIS_KEYS_EXTRACT,
    TicketTypes.REDIS_KEYS_DELETE,
    TicketTypes.REDIS_BACKUP,
    TicketTypes.REDIS_PURGE,
  ];

  const mysqlTicketType = [
    TicketTypes.MYSQL_AUTHORIZE_RULES,
    TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES,
  ];

  const clusterTicketType = [
    TicketTypes.REDIS_PROXY_CLOSE,
    TicketTypes.REDIS_PROXY_OPEN,
    TicketTypes.REDIS_DESTROY,
    TicketTypes.ES_DISABLE,
    TicketTypes.ES_DESTROY,
    TicketTypes.ES_ENABLE,
    TicketTypes.HDFS_ENABLE,
    TicketTypes.HDFS_DISABLE,
    TicketTypes.HDFS_DESTROY,
    TicketTypes.KAFKA_ENABLE,
    TicketTypes.KAFKA_DISABLE,
    TicketTypes.KAFKA_DESTROY,
    TicketTypes.PULSAR_ENABLE,
    TicketTypes.PULSAR_DISABLE,
    TicketTypes.PULSAR_DESTROY,
  ];

  const mysqlClusterTicketType = [
    TicketTypes.MYSQL_HA_DISABLE,
    TicketTypes.MYSQL_SINGLE_DISABLE,
    TicketTypes.MYSQL_HA_ENABLE,
    TicketTypes.MYSQL_SINGLE_ENABLE,
    TicketTypes.MYSQL_HA_DESTROY,
    TicketTypes.MYSQL_SINGLE_DESTROY,
  ];

  const bigDataReplaceType = [
    TicketTypes.ES_REPLACE,
    TicketTypes.HDFS_REPLACE,
    TicketTypes.KAFKA_REPLACE,
    TicketTypes.PULSAR_REPLACE,
  ];

  const mysqlSlaveType = [
    TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE,
    TicketTypes.MYSQL_ADD_SLAVE,
  ];

  const bigDataRebootType = [
    TicketTypes.HDFS_REBOOT,
    TicketTypes.ES_REBOOT,
    TicketTypes.KAFKA_REBOOT,
    TicketTypes.PULSAR_REBOOT,
  ];

  const bigDataCapacityType = [
    TicketTypes.ES_SCALE_UP,
    TicketTypes.ES_SHRINK,
    TicketTypes.HDFS_SCALE_UP,
    TicketTypes.HDFS_SHRINK,
    TicketTypes.KAFKA_SCALE_UP,
    TicketTypes.KAFKA_SHRINK,
    TicketTypes.PULSAR_SHRINK,
    TicketTypes.PULSAR_SCALE_UP,
  ];

  const clones = [
    TicketTypes.MYSQL_CLIENT_CLONE_RULES,
    TicketTypes.MYSQL_INSTANCE_CLONE_RULES,
    TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES,
    TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES,
  ];

  const influxdbTypes = [
    TicketTypes.INFLUXDB_DISABLE,
    TicketTypes.INFLUXDB_REBOOT,
    TicketTypes.INFLUXDB_ENABLE,
    TicketTypes.INFLUXDB_DESTROY,
  ];

  const spiderMasterSlaveTypes = [
    TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH,
    TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER,
  ];

  const spiderAuthorizeRulesTypes = [
    TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES,
  ];

  const importSQLTypes = [
    TicketTypes.MYSQL_IMPORT_SQLFILE,
    TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE,
  ];

  const redisCLBTypes = [
    TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB,
    TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB,
    TicketTypes.REDIS_PLUGIN_CREATE_CLB,
    TicketTypes.REDIS_PLUGIN_DELETE_CLB,
  ];

  // 单一情况映射表
  const SingleDemandMap = {
    [TicketTypes.ES_APPLY]: DetailsES,
    [TicketTypes.HDFS_APPLY]: DetailsHDFS,
    [TicketTypes.INFLUXDB_APPLY]: DetailsInfluxDB,
    [TicketTypes.INFLUXDB_REPLACE]: InfluxdbReplace,
    [TicketTypes.KAFKA_APPLY]: DetailsKafka,
    [TicketTypes.MYSQL_HA_RENAME_DATABASE]: MySQLRename,
    [TicketTypes.MYSQL_PROXY_SWITCH]: MySQLProxySwitch,
    [TicketTypes.MYSQL_HA_DB_TABLE_BACKUP]: MySQLTableBackup,
    [TicketTypes.MYSQL_HA_TRUNCATE_DATA]: MySQLHATruncate,
    [TicketTypes.MYSQL_MIGRATE_CLUSTER]: MySQLMigrateCluster,
    [TicketTypes.MYSQL_MASTER_SLAVE_SWITCH]: MySQLMasterSlaveSwitch,
    [TicketTypes.MYSQL_PROXY_ADD]: MySQLProxyAdd,
    [TicketTypes.MYSQL_MASTER_FAIL_OVER]: MySQLMasterFailOver,
    [TicketTypes.MYSQL_FLASHBACK]: MySQLFlashback,
    [TicketTypes.MYSQL_ROLLBACK_CLUSTER]: MySQLRollbackCluster,
    [TicketTypes.MYSQL_RESTORE_SLAVE]: MySQLRestoreSlave,
    [TicketTypes.MYSQL_HA_FULL_BACKUP]: MySQLFullBackup,
    [TicketTypes.MYSQL_CHECKSUM]: MySQLChecksum,
    [TicketTypes.PULSAR_APPLY]: DetailsPulsar,
    [TicketTypes.REDIS_CLUSTER_APPLY]: DetailsRedis,
    [TicketTypes.REDIS_CLUSTER_CUTOFF]: RedisDBReplace,
    [TicketTypes.REDIS_PROXY_SCALE_UP]: RedisProxyScaleUp,
    [TicketTypes.REDIS_PROXY_SCALE_DOWN]: RedisProxyScaleDown,
    [TicketTypes.REDIS_SCALE_UPDOWN]: RedisClusterCapacityUpdate,
    [TicketTypes.REDIS_MASTER_SLAVE_SWITCH]: RedisMasterFailover,
    [TicketTypes.REDIS_DATA_STRUCTURE]: RedisDataStructure,
    [TicketTypes.REDIS_DATA_STRUCTURE_TASK_DELETE]: RedisStructureDelete,
    [TicketTypes.REDIS_CLUSTER_ADD_SLAVE]: RedisAddSlave,
    [TicketTypes.REDIS_CLUSTER_DATA_COPY]: RedisDataCopy,
    [TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE]: RedisClusterShardUpdate,
    [TicketTypes.REDIS_CLUSTER_TYPE_UPDATE]: RedisClusterTypeUpdate,
    [TicketTypes.REDIS_DATACOPY_CHECK_REPAIR]: RedisDataCheckAndRepair,
    [TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY]: RedisRollbackDataCopy,
    [TicketTypes.TENDBCLUSTER_APPLY]: DetailsSpider,
    [TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES]: SpiderAddNodes,
    [TicketTypes.TENDBCLUSTER_CHECKSUM]: SpiderCheckSum,
    [TicketTypes.TENDBCLUSTER_DESTROY]: SpiderDestroy,
    [TicketTypes.TENDBCLUSTER_DISABLE]: SpiderDisable,
    [TicketTypes.TENDBCLUSTER_ENABLE]: SpiderEnable,
    [TicketTypes.TENDBCLUSTER_FLASHBACK]: SpiderFlashback,
    [TicketTypes.TENDBCLUSTER_FULL_BACKUP]: SpiderFullBackup,
    [TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY]: SpiderMNTApply,
    [TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY]: SpiderMNTDestroy,
    [TicketTypes.TENDBCLUSTER_NODE_REBALANCE]: SpiderNodeRebalance,
    [TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES]: SpiderReduceNodes,
    [TicketTypes.TENDBCLUSTER_RENAME_DATABASE]: SpiderRenameDatabase,
    [TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER]: SpiderRollback,
    [TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY]: SpiderSlaveApply,
    [TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_DESTROY]: SpiderSlaveDestroy,
    [TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP]: SpiderTableBackup,
    [TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE]: SpiderTruncateDatabase,
    [TicketTypes.TENDBCLUSTER_PARTITION]: SpiderPartitionManage,
  };

  // 不同集群详情组件
  const detailsComp = computed(() => {
    const ticketType = props.data.ticket_type;
    // M权限克隆
    if (clones.includes(ticketType)) {
      return MySQLClone;
    }
    // MySQL Slave
    if (mysqlSlaveType.includes(ticketType)) {
      return MySQLSlave;
    }
    // Redis、大数据启停删单据
    if (clusterTicketType.includes(ticketType)) {
      return DetailsClusterOperation;
    }
    // 大数据替换单据
    if (bigDataReplaceType.includes(ticketType)) {
      return BigDataReplace;
    }
    if (redisKeysType.includes(ticketType)) {
      return RedisOperation;
    }
    if (mysqlTicketType.includes(ticketType)) {
      return MySQLOperation;
    }
    // influxdb 禁用/重启/启用/删除
    if (influxdbTypes.includes(ticketType)) {
      return InfluxdbOperations;
    }
    // 大数据实例重启
    if (bigDataRebootType.includes(ticketType)) {
      return BigDataReboot;
    }
    // MySQL 启停删
    if (mysqlClusterTicketType.includes(ticketType)) {
      return MySQLClusterOperation;
    }
    // 大数据扩缩容
    if (bigDataCapacityType.includes(ticketType)) {
      return BigDataExpansionCapacity;
    }
    // Spider 主从相关
    if (spiderMasterSlaveTypes.includes(ticketType)) {
      return SpiderMasterSlaveSwitch;
    }
    // spider 授权规则
    if (spiderAuthorizeRulesTypes.includes(ticketType)) {
      return SpiderAuthorizeRules;
    }
    // SQL执行
    if (importSQLTypes.includes(ticketType)) {
      return MySQLImportSQLFile;
    }
    // redis CLB 相关
    if (redisCLBTypes.includes(ticketType)) {
      return CLBDetail;
    }
    if (ticketType in SingleDemandMap) {
      return SingleDemandMap[ticketType as keyof typeof SingleDemandMap];
    }
    return DetailsMySQL;
  });


</script>

<style lang="less" scoped>
  .ticket-details {
    padding: 24px;

    .db-card {
      margin-bottom: 16px;

      .is-fullscreen {
        position: fixed;
        top: 0;
        right: 0;
        z-index: 9999;
        width: 100%;
        height: 100%;
      }
    }
  }
</style>
