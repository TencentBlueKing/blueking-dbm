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
  import _ from 'lodash';
  import type { RouteRecordRaw } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import DetailsClusterOperation from './bigdata/DetailsClusterOperation.vue';
  import DetailDoris from './bigdata/DetailsDoris.vue';
  import DetailsES from './bigdata/DetailsES.vue';
  import DetailsHDFS from './bigdata/DetailsHDFS.vue';
  import DetailsInfluxDB from './bigdata/DetailsInfluxDB.vue';
  import DetailsKafka from './bigdata/DetailsKafka.vue';
  import DetailsPulsar from './bigdata/DetailsPulsar.vue';
  import DetailRiak from './bigdata/DetailsRiak.vue';
  import BigDataExpansionCapacity from './bigdata/expansion-capacity/Index.vue';
  import BigDataReboot from './bigdata/Reboot.vue';
  import BigDataReplace from './bigdata/Replace.vue';
  import RiakExpansionCapacity from './bigdata/RiakExpansionCapacity.vue';
  import RiakReboot from './bigdata/RiakReboot.vue';
  import DefaultDetails from './Default.vue';
  import InfluxdbOperations from './influxdb/Operations.vue';
  import InfluxdbReplace from './influxdb/Replace.vue';
  import MongoAuthrizeRules from './mongodb/AuthorizeRules.vue';
  import MongoCapacityChange from './mongodb/CapacityChange.vue';
  import MongoDbBackup from './mongodb/DbBackup.vue';
  import MongoDbClear from './mongodb/DbClear.vue';
  import MongoDBReplace from './mongodb/DBReplace.vue';
  import MongoDbStruct from './mongodb/DbStruct.vue';
  import MongoDbTableBackup from './mongodb/DbTableBackup.vue';
  import MongoDetailsClusterOperation from './mongodb/DetailsClusterOperation.vue';
  import DetailsMongoDBReplicaSet from './mongodb/DetailsMongoDBReplicaSet.vue';
  import DetailsMongoDBSharedCluster from './mongodb/DetailsMongoDBSharedCluster.vue';
  import MongoProxyScaleDown from './mongodb/ProxyScaleDown.vue';
  import MongoProxyScaleUp from './mongodb/ProxyScaleUp.vue';
  import MongoScriptExecute from './mongodb/script-execute/Index.vue';
  import MongoShardScaleDown from './mongodb/ShardScaleDown.vue';
  import MongoShardScaleUp from './mongodb/ShardScaleUp.vue';
  import MongoTemporaryDestrot from './mongodb/TemporaryDestrot.vue';
  import MySQLAccountRuleChange from './mysql/account-rule-change/Index.vue';
  import MySQLAuthorizeRule from './mysql/authorize-rule/Index.vue';
  import MySQLChecksum from './mysql/Checksum.vue';
  import MySQLClone from './mysql/Clone.vue';
  import MySQLClusterOperation from './mysql/ClusterOperation.vue';
  import MySQLDataMigrate from './mysql/DataMigrate.vue';
  import DetailsMySQL from './mysql/Details.vue';
  import DumperInstall from './mysql/DumperInstall.vue';
  import DumperNodeStatusUpdate from './mysql/DumperNodeStatusUpdate.vue';
  import DumperSwitchNode from './mysql/DumperSwitchNode.vue';
  import MysqlExportData from './mysql/ExportData.vue';
  import MySQLFlashback from './mysql/Flashback.vue';
  import MySQLFullBackup from './mysql/FullBackup.vue';
  import MySQLHATruncate from './mysql/HATruncate.vue';
  import MySQLImportSQLFile from './mysql/import-sql-file/Index.vue';
  import MySQLMasterFailOver from './mysql/MasterFailOver.vue';
  import MySQLMasterSlaveSwitch from './mysql/MasterSlaveSwitch.vue';
  import MySQLMigrateCluster from './mysql/MigrateCluster.vue';
  import MysqlOpenArea from './mysql/openarea/Index.vue';
  import MysqlParition from './mysql/Partition.vue';
  import MySQLProxyReplace from './mysql/proxy-replace/Index.vue';
  import MySQLProxyAdd from './mysql/ProxyAdd.vue';
  import MySQLRename from './mysql/Rename.vue';
  import MySQLRestoreLocalSlave from './mysql/RestoreLocalSlave.vue';
  import MySQLRestoreSlave from './mysql/RestoreSlave.vue';
  import MySQLRollback from './mysql/rollback/Index.vue';
  import MySQLAddSlave from './mysql/SlaveAdd.vue';
  import MySQLTableBackup from './mysql/TableBackup.vue';
  import MySQLVerisonLocalUpgrade from './mysql/version-upgrade/VersionLocalUpgrade.vue';
  import MySQLVerisonMigrateUpgrade from './mysql/version-upgrade/VersionMigrateUpgrade.vue';
  import MySQLVerisonProxyUpgrade from './mysql/version-upgrade/VersionProxyUpgrade.vue';
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
  import DetailsRedisHa from './redis/DetailsHa.vue';
  import RedisHaClusterOperation from './redis/HaClusterOperation.vue';
  import RedisMasterFailover from './redis/MasterFailover.vue';
  import RedisOperation from './redis/Operation.vue';
  import RedisProxyScaleDown from './redis/ProxyScaleDown.vue';
  import RedisProxyScaleUp from './redis/ProxyScaleUp.vue';
  import RedisRollbackDataCopy from './redis/RollbackDataCopy.vue';
  import RedisStructureDelete from './redis/StructureDelete.vue';
  import RedisVersionUpgrade from './redis/VersionUpgrade.vue';
  import SpiderAccountRuleChange from './spider/AccountRuleChange.vue';
  import SpiderAddNodes from './spider/AddNodes.vue';
  import SpiderAuthorizeRules from './spider/AuthorizeRules.vue';
  import SpiderCheckSum from './spider/CheckSum.vue';
  import SpiderDestroy from './spider/Destroy.vue';
  import DetailsSpider from './spider/Details.vue';
  import SpiderDisable from './spider/Disable.vue';
  import SpiderEnable from './spider/Enable.vue';
  import SpiderFlashback from './spider/Flashback.vue';
  import SpiderFullBackup from './spider/FullBackup.vue';
  import SpiderMasterFailOver from './spider/MasterFailOver.vue';
  import SpiderMasterSlaveSwitch from './spider/MasterSlaveSwitch.vue';
  import SpiderMigrateCluster from './spider/MigrateCluster.vue';
  import SpiderMNTApply from './spider/MNTApply.vue';
  import SpiderMNTDestroy from './spider/MNTDestroy.vue';
  import SpiderNodeRebalance from './spider/NodeRebalance.vue';
  import SpiderReduceNodes from './spider/ReduceNodes.vue';
  import SpiderRenameDatabase from './spider/RenameDatabase.vue';
  import SpiderRollback from './spider/rollback/Index.vue';
  import SpiderSlaveApply from './spider/SlaveApply.vue';
  import SpiderSlaveDestroy from './spider/SlaveDestroy.vue';
  import SpiderSlaveRebuild from './spider/SlaveRebuild.vue';
  import SpiderTableBackup from './spider/TableBackup.vue';
  import SpiderTruncateDatabase from './spider/TruncateDatabase.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const sqlserverDetailModule = import.meta.glob<{ default: () => RouteRecordRaw[] }>('./sqlserver/*.vue', {
    eager: true,
  });

  const mysqlTicketType = [TicketTypes.MYSQL_AUTHORIZE_RULES, TicketTypes.MYSQL_EXCEL_AUTHORIZE_RULES];

  const mysqlTruncateDataTypes = [TicketTypes.MYSQL_HA_TRUNCATE_DATA, TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA];

  const mysqlApplyTypes = [TicketTypes.MYSQL_SINGLE_APPLY, TicketTypes.MYSQL_HA_APPLY];

  const mysqlClusterTicketType = [
    TicketTypes.MYSQL_HA_DISABLE,
    TicketTypes.MYSQL_SINGLE_DISABLE,
    TicketTypes.MYSQL_HA_ENABLE,
    TicketTypes.MYSQL_SINGLE_ENABLE,
    TicketTypes.MYSQL_HA_DESTROY,
    TicketTypes.MYSQL_SINGLE_DESTROY,
  ];

  const dumperNodeStatusUpdateType = [TicketTypes.TBINLOGDUMPER_DISABLE_NODES, TicketTypes.TBINLOGDUMPER_ENABLE_NODES];

  const redisKeysType = [
    TicketTypes.REDIS_KEYS_EXTRACT,
    TicketTypes.REDIS_KEYS_DELETE,
    TicketTypes.REDIS_BACKUP,
    TicketTypes.REDIS_PURGE,
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
    TicketTypes.RIAK_CLUSTER_DISABLE,
    TicketTypes.RIAK_CLUSTER_ENABLE,
    TicketTypes.RIAK_CLUSTER_DESTROY,
    TicketTypes.DORIS_DISABLE,
    TicketTypes.DORIS_ENABLE,
    TicketTypes.DORIS_DESTROY,
  ];

  // const sqlserverApplyTiketType = [TicketTypes.SQLSERVER_SINGLE_APPLY, TicketTypes.SQLSERVER_HA_APPLY];

  // const sqlserverClusterTicketType = [
  //   TicketTypes.SQLSERVER_DISABLE,
  //   TicketTypes.SQLSERVER_ENABLE,
  //   TicketTypes.SQLSERVER_DESTROY,
  // ];

  const bigDataReplaceType = [
    TicketTypes.ES_REPLACE,
    TicketTypes.HDFS_REPLACE,
    TicketTypes.KAFKA_REPLACE,
    TicketTypes.PULSAR_REPLACE,
    TicketTypes.DORIS_REPLACE,
  ];

  const spiderSlaveType = [TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE, TicketTypes.TENDBCLUSTER_RESTORE_SLAVE];

  const bigDataRebootType = [
    TicketTypes.HDFS_REBOOT,
    TicketTypes.ES_REBOOT,
    TicketTypes.KAFKA_REBOOT,
    TicketTypes.PULSAR_REBOOT,
    TicketTypes.DORIS_REBOOT,
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
    TicketTypes.DORIS_SHRINK,
    TicketTypes.DORIS_SCALE_UP,
  ];

  const riakCapacityType = [TicketTypes.RIAK_CLUSTER_SCALE_IN, TicketTypes.RIAK_CLUSTER_SCALE_OUT];

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

  const spiderAuthorizeRulesTypes = [
    TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES,
  ];

  const importSQLTypes = [
    TicketTypes.MYSQL_IMPORT_SQLFILE,
    TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE,
    TicketTypes.TENDBCLUSTER_FORCE_IMPORT_SQLFILE,
    TicketTypes.MYSQL_FORCE_IMPORT_SQLFILE,
  ];

  const redisCLBTypes = [
    TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB,
    TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB,
    TicketTypes.REDIS_PLUGIN_CREATE_CLB,
    TicketTypes.REDIS_PLUGIN_DELETE_CLB,
  ];

  const mongoClusterOprationTypes = [
    TicketTypes.MONGODB_ENABLE,
    TicketTypes.MONGODB_DISABLE,
    TicketTypes.MONGODB_DESTROY,
  ];

  const mongoAuthorizeRulesTypes = [TicketTypes.MONGODB_AUTHORIZE_RULES, TicketTypes.MONGODB_EXCEL_AUTHORIZE];

  // const sqlserverAuthorizeRulesTypes = [
  //   TicketTypes.SQLSERVER_AUTHORIZE_RULES,
  //   TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES,
  // ];

  const redisHaOperationTypes = [
    TicketTypes.REDIS_INSTANCE_CLOSE,
    TicketTypes.REDIS_INSTANCE_OPEN,
    TicketTypes.REDIS_INSTANCE_DESTROY,
  ];

  const openareaTypes = [TicketTypes.MYSQL_OPEN_AREA, TicketTypes.TENDBCLUSTER_OPEN_AREA];

  const dataExportTypes = [TicketTypes.MYSQL_DUMP_DATA, TicketTypes.TENDBCLUSTER_DUMP_DATA];

  // 单一情况映射表
  const SingleDemandMap = {
    [TicketTypes.ES_APPLY]: DetailsES,
    [TicketTypes.HDFS_APPLY]: DetailsHDFS,
    [TicketTypes.INFLUXDB_APPLY]: DetailsInfluxDB,
    [TicketTypes.INFLUXDB_REPLACE]: InfluxdbReplace,
    [TicketTypes.KAFKA_APPLY]: DetailsKafka,
    [TicketTypes.MYSQL_PROXY_SWITCH]: MySQLProxyReplace,
    [TicketTypes.MYSQL_HA_DB_TABLE_BACKUP]: MySQLTableBackup,
    [TicketTypes.MYSQL_MIGRATE_CLUSTER]: MySQLMigrateCluster,
    [TicketTypes.MYSQL_PROXY_ADD]: MySQLProxyAdd,
    [TicketTypes.MYSQL_MASTER_FAIL_OVER]: MySQLMasterFailOver,
    [TicketTypes.MYSQL_FLASHBACK]: MySQLFlashback,
    [TicketTypes.MYSQL_ROLLBACK_CLUSTER]: MySQLRollback,
    [TicketTypes.MYSQL_RESTORE_SLAVE]: MySQLRestoreSlave,
    [TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE]: MySQLRestoreLocalSlave,
    [TicketTypes.MYSQL_HA_FULL_BACKUP]: MySQLFullBackup,
    [TicketTypes.MYSQL_CHECKSUM]: MySQLChecksum,
    [TicketTypes.MYSQL_ADD_SLAVE]: MySQLAddSlave,
    [TicketTypes.MYSQL_DATA_MIGRATE]: MySQLDataMigrate,
    [TicketTypes.MYSQL_MASTER_SLAVE_SWITCH]: MySQLMasterSlaveSwitch,
    [TicketTypes.MYSQL_ACCOUNT_RULE_CHANGE]: MySQLAccountRuleChange,
    [TicketTypes.TBINLOGDUMPER_INSTALL]: DumperInstall,
    [TicketTypes.TBINLOGDUMPER_SWITCH_NODES]: DumperSwitchNode,
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
    [TicketTypes.REDIS_VERSION_UPDATE_ONLINE]: RedisVersionUpgrade,
    [TicketTypes.TENDBCLUSTER_APPLY]: DetailsSpider,
    [TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES]: SpiderAddNodes,
    [TicketTypes.TENDBCLUSTER_CHECKSUM]: SpiderCheckSum,
    [TicketTypes.TENDBCLUSTER_DESTROY]: SpiderDestroy,
    [TicketTypes.TENDBCLUSTER_DISABLE]: SpiderDisable,
    [TicketTypes.TENDBCLUSTER_ENABLE]: SpiderEnable,
    [TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH]: SpiderMasterSlaveSwitch,
    [TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER]: SpiderMasterFailOver,
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
    [TicketTypes.TENDBCLUSTER_ACCOUNT_RULE_CHANGE]: SpiderAccountRuleChange,
    [TicketTypes.RIAK_CLUSTER_APPLY]: DetailRiak,
    [TicketTypes.RIAK_CLUSTER_REBOOT]: RiakReboot,
    [TicketTypes.MONGODB_SHARD_APPLY]: DetailsMongoDBSharedCluster,
    [TicketTypes.MONGODB_REPLICASET_APPLY]: DetailsMongoDBReplicaSet,
    [TicketTypes.MONGODB_EXEC_SCRIPT_APPLY]: MongoScriptExecute,
    [TicketTypes.MONGODB_ADD_SHARD_NODES]: MongoShardScaleUp,
    [TicketTypes.MONGODB_REDUCE_SHARD_NODES]: MongoShardScaleDown,
    [TicketTypes.MONGODB_REDUCE_MONGOS]: MongoProxyScaleDown,
    [TicketTypes.MONGODB_BACKUP]: MongoDbTableBackup,
    [TicketTypes.MONGODB_FULL_BACKUP]: MongoDbBackup,
    [TicketTypes.MONGODB_REMOVE_NS]: MongoDbClear,
    [TicketTypes.MONGODB_RESTORE]: MongoDbStruct,
    [TicketTypes.MONGODB_CUTOFF]: MongoDBReplace,
    [TicketTypes.MONGODB_SCALE_UPDOWN]: MongoCapacityChange,
    [TicketTypes.MONGODB_ADD_MONGOS]: MongoProxyScaleUp,
    [TicketTypes.MONGODB_TEMPORARY_DESTROY]: MongoTemporaryDestrot,
    [TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER]: SpiderMigrateCluster,
    [TicketTypes.REDIS_INS_APPLY]: DetailsRedisHa,
    [TicketTypes.MYSQL_PROXY_UPGRADE]: MySQLVerisonProxyUpgrade,
    [TicketTypes.MYSQL_LOCAL_UPGRADE]: MySQLVerisonLocalUpgrade,
    [TicketTypes.MYSQL_MIGRATE_UPGRADE]: MySQLVerisonMigrateUpgrade,
    [TicketTypes.DORIS_APPLY]: DetailDoris,
  };

  // 不同集群详情组件
  const detailsComp = computed(() => {
    const ticketType = props.data.ticket_type;

    const renderModule = _.find(
      Object.values(sqlserverDetailModule),
      (moduleItem) => moduleItem.default.name === ticketType,
    );

    if (renderModule) {
      return renderModule.default;
    }

    // M权限克隆
    if (clones.includes(ticketType)) {
      return MySQLClone;
    }
    // MySQL 清档
    if (mysqlTruncateDataTypes.includes(ticketType)) {
      return MySQLHATruncate;
    }
    // MySQL 重命名
    if ([TicketTypes.MYSQL_HA_RENAME_DATABASE, TicketTypes.MYSQL_SINGLE_RENAME_DATABASE].includes(ticketType)) {
      return MySQLRename;
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
      return MySQLAuthorizeRule;
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
    // Riak 扩缩容
    if (riakCapacityType.includes(ticketType)) {
      return RiakExpansionCapacity;
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
    // dumper 节点状态变更
    if (dumperNodeStatusUpdateType.includes(ticketType)) {
      return DumperNodeStatusUpdate;
    }
    // mongo 启停删
    if (mongoClusterOprationTypes.includes(ticketType)) {
      return MongoDetailsClusterOperation;
    }
    // mongo 授权
    if (mongoAuthorizeRulesTypes.includes(ticketType)) {
      return MongoAuthrizeRules;
    }
    // // SQLServer 申请
    // if (sqlserverApplyTiketType.includes(ticketType)) {
    //   return SqlserverDetails;
    // }
    // // SQLServer 启停删
    // if (sqlserverClusterTicketType.includes(ticketType)) {
    //   return SqlserverClusterOperation;
    // }
    // // SQLServer 授权
    // if (sqlserverAuthorizeRulesTypes.includes(ticketType)) {
    //   return SqlserverAuthrizeRules;
    // }
    // Spider 重建从库
    if (spiderSlaveType.includes(ticketType)) {
      return SpiderSlaveRebuild;
    }
    // Redis 主从集群启停删
    if (redisHaOperationTypes.includes(ticketType)) {
      return RedisHaClusterOperation;
    }
    // 开区
    if (openareaTypes.includes(ticketType)) {
      return MysqlOpenArea;
    }
    // mysql 部署
    if (mysqlApplyTypes.includes(ticketType)) {
      return DetailsMySQL;
    }
    if (ticketType in SingleDemandMap) {
      return SingleDemandMap[ticketType as keyof typeof SingleDemandMap];
    }
    if ([TicketTypes.MYSQL_PARTITION, TicketTypes.TENDBCLUSTER_PARTITION].includes(ticketType)) {
      return MysqlParition;
    }
    if (dataExportTypes.includes(ticketType)) {
      return MysqlExportData;
    }
    if ([TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE, TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE].includes(ticketType)) {
      return MySQLRestoreLocalSlave;
    }
    if ([TicketTypes.MYSQL_RESTORE_SLAVE, TicketTypes.SQLSERVER_RESTORE_SLAVE].includes(ticketType)) {
      return MySQLRestoreSlave;
    }

    if ([TicketTypes.MYSQL_MASTER_SLAVE_SWITCH, TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH].includes(ticketType)) {
      return MySQLMasterSlaveSwitch;
    }

    return DefaultDetails;
  });
</script>

<style lang="less" scoped>
  .ticket-details {
    // padding: 24px;

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
