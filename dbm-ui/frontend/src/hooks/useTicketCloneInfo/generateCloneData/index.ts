import TicketModel from '@services/model/ticket/ticket';

import { TicketTypes } from '@common/const';

import {
  generateMysqlAuthorizeRuleCloneData,
  generateMysqlChecksumCloneData,
  generateMysqlClientCloneData,
  generateMysqlDataMigrateCloneData,
  generateMysqlDbBackupCloneData,
  generateMysqlDbClearCloneData,
  generateMysqlDbRenameCloneData,
  generateMysqlDbTableBackupCloneData,
  generateMysqlFlashbackCloneData,
  generateMysqlHaApplyCloneData,
  generateMysqlImportSqlFileCloneData,
  generateMysqlInstanceCloneData,
  generateMysqlMasterFailoverCloneData,
  generateMysqlMasterSlaveSwicthCloneData,
  generateMysqlMigrateClusterCloneData,
  generateMysqlOpenAreaCloneData,
  generateMysqlProxyAddCloneData,
  generateMysqlProxyReplaceCloneData,
  generateMysqlRestoreLocalSlaveCloneData,
  generateMysqlRestoreSlaveCloneData,
  generateMysqlRollbackCloneData,
  generateMysqlSingleApplyCloneData,
  generateMysqlSlaveAddCloneData,
  generateMysqlVersionLocalUpgradeCloneData,
  generateMysqlVersionMigrateUpgradeCloneData,
  generateMysqlVersionProxyUpgradeCloneData,
} from './mysql';
import {
  generateRedisApplyCloneData,
  generateRedisClusterAddSlaveCloneData,
  generateRedisClusterCutoffCloneData,
  generateRedisClusterShardUpdateCloneData,
  generateRedisClusterTypeUpdateCloneData,
  generateRedisDataCopyCheckRepairCloneData,
  generateRedisDataCopyCloneData,
  generateRedisDataStructureCloneData,
  generateRedisMasterSlaveSwitchCloneData,
  generateRedisOperationCloneData,
  generateRedisProxyScaleDownCloneData,
  generateRedisProxyScaleUpCloneData,
  generateRedisRedisVersionUpgradeCloneData,
  generateRedisRollbackDataCloneData,
  generateRedisScaleUpdownCloneData,
} from './redis';
import {
  generateSpiderAddMntDataCloneData,
  generateSpiderApplyCloneData,
  generateSpiderAuthorizeRuleCloneData,
  generateSpiderCapacityChangeCloneData,
  generateSpiderChecksumCloneData,
  generateSpiderDbBackupCloneData,
  generateSpiderDbClearCloneData,
  generateSpiderDbRenameCloneData,
  generateSpiderDbTableBackupCloneData,
  generateSpiderFlashbackCloneData,
  generateSpiderMasterFailoverCloneData,
  generateSpiderMasterSlaveCloneCloneData,
  generateSpiderMasterSlaveSwapCloneData,
  generateSpiderPrivilegeCloneClientCloneData,
  generateSpiderPrivilegeCloneInstCloneData,
  generateSpiderProxyScaleDownCloneData,
  generateSpiderProxyScaleUpCloneData,
  generateSpiderProxySlaveApplyCloneData,
  // generateSpiderRollbackCloneData,
  generateSpiderSlaveRebuildLocalCloneData,
  generateSpiderSlaveRebuildNewCloneData,
  generateSpiderSqlExecuteCloneData,
} from './spider';
import { generateSpiderRollbackCloneData } from './tendbcluster/rollback';

export const generateCloneDataHandlerMap = {
  [TicketTypes.REDIS_CLUSTER_APPLY]: generateRedisApplyCloneData,
  [TicketTypes.REDIS_PROXY_SCALE_UP]: generateRedisProxyScaleUpCloneData, // Redis 接入层扩容
  [TicketTypes.REDIS_PROXY_SCALE_DOWN]: generateRedisProxyScaleDownCloneData, // Redis 接入层缩容
  [TicketTypes.REDIS_SCALE_UPDOWN]: generateRedisScaleUpdownCloneData, // Redis 集群容量变更
  [TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE]: generateRedisClusterShardUpdateCloneData, // Redis 集群分片数变更
  [TicketTypes.REDIS_CLUSTER_TYPE_UPDATE]: generateRedisClusterTypeUpdateCloneData, // Redis 集群类型变更
  [TicketTypes.REDIS_DATA_STRUCTURE]: generateRedisDataStructureCloneData, // Redis 定点构造
  [TicketTypes.REDIS_MASTER_SLAVE_SWITCH]: generateRedisMasterSlaveSwitchCloneData, // Redis 主从切换
  [TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY]: generateRedisRollbackDataCloneData, // Redis 以构造实例恢复
  [TicketTypes.REDIS_CLUSTER_DATA_COPY]: generateRedisDataCopyCloneData, // Redis 集群数据复制
  [TicketTypes.REDIS_DATACOPY_CHECK_REPAIR]: generateRedisDataCopyCheckRepairCloneData, // Redis 数据校验与修复
  [TicketTypes.REDIS_CLUSTER_ADD_SLAVE]: generateRedisClusterAddSlaveCloneData, // Redis 重建从库
  [TicketTypes.REDIS_CLUSTER_CUTOFF]: generateRedisClusterCutoffCloneData, // Redis 整机替换
  [TicketTypes.REDIS_KEYS_EXTRACT]: generateRedisOperationCloneData, // Redis 提取Key
  [TicketTypes.REDIS_KEYS_DELETE]: generateRedisOperationCloneData, // Redis 删除Key
  [TicketTypes.REDIS_BACKUP]: generateRedisOperationCloneData, // Redis 集群备份
  [TicketTypes.REDIS_PURGE]: generateRedisOperationCloneData,
  [TicketTypes.MYSQL_AUTHORIZE_RULES]: generateMysqlAuthorizeRuleCloneData, // Mysql 集群授权
  [TicketTypes.MYSQL_IMPORT_SQLFILE]: generateMysqlImportSqlFileCloneData, // Mysql SQL变更执行
  [TicketTypes.MYSQL_CHECKSUM]: generateMysqlChecksumCloneData, // Mysql 数据校验
  [TicketTypes.MYSQL_CLIENT_CLONE_RULES]: generateMysqlClientCloneData, // Mysql 客户端权限克隆
  [TicketTypes.MYSQL_INSTANCE_CLONE_RULES]: generateMysqlInstanceCloneData, // Mysql DB实例权限克隆
  [TicketTypes.MYSQL_HA_APPLY]: generateMysqlHaApplyCloneData, // MySQL 高可用部署
  [TicketTypes.MYSQL_SINGLE_APPLY]: generateMysqlSingleApplyCloneData, // MySQL 单节点部署
  [TicketTypes.MYSQL_HA_DB_TABLE_BACKUP]: generateMysqlDbTableBackupCloneData, // Mysql 库表备份
  [TicketTypes.MYSQL_HA_RENAME_DATABASE]: generateMysqlDbRenameCloneData, // MySQL 高可用DB重命名
  [TicketTypes.MYSQL_SINGLE_RENAME_DATABASE]: generateMysqlDbRenameCloneData, // MySQL 单节点DB重命名
  [TicketTypes.MYSQL_HA_FULL_BACKUP]: generateMysqlDbBackupCloneData, // Mysql 全库备份
  [TicketTypes.MYSQL_FLASHBACK]: generateMysqlFlashbackCloneData, // MySQL 闪回
  [TicketTypes.MYSQL_RESTORE_LOCAL_SLAVE]: generateMysqlRestoreLocalSlaveCloneData, // MySQL 重建从库-原地重建
  [TicketTypes.MYSQL_RESTORE_SLAVE]: generateMysqlRestoreSlaveCloneData, // MySQL 重建从库-原地重建
  [TicketTypes.MYSQL_ADD_SLAVE]: generateMysqlSlaveAddCloneData, // MySQL 添加从库
  [TicketTypes.MYSQL_MIGRATE_CLUSTER]: generateMysqlMigrateClusterCloneData, // MySQL 迁移(克隆)主从
  [TicketTypes.MYSQL_MASTER_SLAVE_SWITCH]: generateMysqlMasterSlaveSwicthCloneData, // MySQL 主从互换
  [TicketTypes.MYSQL_PROXY_SWITCH]: generateMysqlProxyReplaceCloneData, // MySQL 替换Proxy
  [TicketTypes.MYSQL_PROXY_ADD]: generateMysqlProxyAddCloneData, // MySQL 添加Proxy
  [TicketTypes.MYSQL_MASTER_FAIL_OVER]: generateMysqlMasterFailoverCloneData, // MySQL 主库故障切换
  [TicketTypes.MYSQL_HA_TRUNCATE_DATA]: generateMysqlDbClearCloneData, // MySQL 高可用清档
  [TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA]: generateMysqlDbClearCloneData, // MySQL 单节点清档
  [TicketTypes.MYSQL_OPEN_AREA]: generateMysqlOpenAreaCloneData, // Mysql 开区
  [TicketTypes.MYSQL_DATA_MIGRATE]: generateMysqlDataMigrateCloneData, // Mysql DB克隆
  [TicketTypes.MYSQL_PROXY_UPGRADE]: generateMysqlVersionProxyUpgradeCloneData, // MySQL Proxy 升级
  [TicketTypes.MYSQL_LOCAL_UPGRADE]: generateMysqlVersionLocalUpgradeCloneData, // MySQL 原地升级
  [TicketTypes.MYSQL_MIGRATE_UPGRADE]: generateMysqlVersionMigrateUpgradeCloneData, // MySQL 迁移升级
  [TicketTypes.MYSQL_ROLLBACK_CLUSTER]: generateMysqlRollbackCloneData, // MySQL 定点构造
  [TicketTypes.TENDBCLUSTER_ROLLBACK_CLUSTER]: generateSpiderRollbackCloneData, // Tendbcluster 定点构造
  [TicketTypes.TENDBCLUSTER_OPEN_AREA]: generateMysqlOpenAreaCloneData, // Spider 开区
  [TicketTypes.REDIS_VERSION_UPDATE_ONLINE]: generateRedisRedisVersionUpgradeCloneData, // Redis 版本升级
  [TicketTypes.TENDBCLUSTER_APPLY]: generateSpiderApplyCloneData, // spider 集群部署
  [TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES]: generateSpiderProxyScaleUpCloneData, // Spider扩容接入层
  [TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES]: generateSpiderProxyScaleDownCloneData, // Spider缩容接入层
  [TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY]: generateSpiderProxySlaveApplyCloneData, // Spider 部署只读接入层
  [TicketTypes.TENDBCLUSTER_SPIDER_MNT_APPLY]: generateSpiderAddMntDataCloneData, // Spider 添加运维节点
  [TicketTypes.TENDBCLUSTER_MASTER_SLAVE_SWITCH]: generateSpiderMasterSlaveSwapCloneData, // Spider remote 主从切换
  [TicketTypes.TENDBCLUSTER_RENAME_DATABASE]: generateSpiderDbRenameCloneData, // Spider Tendbcluster 重命名
  [TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER]: generateSpiderMasterFailoverCloneData, // Spider remote主故障切换
  [TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP]: generateSpiderDbTableBackupCloneData, // Spider TenDBCluster 库表备份
  [TicketTypes.TENDBCLUSTER_FULL_BACKUP]: generateSpiderDbBackupCloneData, // Spider TenDBCluster 全备单据
  [TicketTypes.TENDBCLUSTER_NODE_REBALANCE]: generateSpiderCapacityChangeCloneData, // Spider 集群remote节点扩缩容
  [TicketTypes.TENDBCLUSTER_FLASHBACK]: generateSpiderFlashbackCloneData, // Spider 闪回
  [TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE]: generateSpiderDbClearCloneData, // Spider tendbcluster 清档
  [TicketTypes.TENDBCLUSTER_CHECKSUM]: generateSpiderChecksumCloneData, // Spider checksum
  [TicketTypes.TENDBCLUSTER_CLIENT_CLONE_RULES]: generateSpiderPrivilegeCloneClientCloneData, // Spider 客户端权限克隆
  [TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES]: generateSpiderPrivilegeCloneInstCloneData, // Spider DB 实例权限克隆
  [TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES]: generateSpiderAuthorizeRuleCloneData, // Spider 集群授权
  [TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE]: generateSpiderSqlExecuteCloneData, // Spider SQL变更执行
  [TicketTypes.TENDBCLUSTER_MIGRATE_CLUSTER]: generateSpiderMasterSlaveCloneCloneData, // spider 迁移主从
  [TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE]: generateSpiderSlaveRebuildLocalCloneData, // spider 重建从库-原地重建
  [TicketTypes.TENDBCLUSTER_RESTORE_SLAVE]: generateSpiderSlaveRebuildNewCloneData, // spider 重建从库-新机重建
};

const importSqlserverModule = <T extends Record<string, any>>() => {
  const modules = import.meta.glob<{ default: () => any }>(`./sqlserver/*.ts`, {
    eager: true,
  });

  return Object.keys(modules).reduce((result, item) => {
    const [, ticketType] = item.match(/([^/]+)\.ts$/) as [string, string];
    return Object.assign(result, {
      [ticketType]: modules[item].default,
    });
  }, {} as T);
};

const sqlserverTicketModule = importSqlserverModule<{
  [TicketTypes.SQLSERVER_ADD_SLAVE]: typeof import('./sqlserver/SQLSERVER_ADD_SLAVE').default;
  [TicketTypes.SQLSERVER_BACKUP_DBS]: typeof import('./sqlserver/SQLSERVER_BACKUP_DBS').default;
  [TicketTypes.SQLSERVER_CLEAR_DBS]: typeof import('./sqlserver/SQLSERVER_CLEAR_DBS').default;
  [TicketTypes.SQLSERVER_DBRENAME]: typeof import('./sqlserver/SQLSERVER_DBRENAME').default;
  [TicketTypes.SQLSERVER_FULL_MIGRATE]: typeof import('./sqlserver/SQLSERVER_FULL_MIGRATE').default;
  [TicketTypes.SQLSERVER_IMPORT_SQLFILE]: typeof import('./sqlserver/SQLSERVER_IMPORT_SQLFILE').default;
  [TicketTypes.SQLSERVER_INCR_MIGRATE]: typeof import('./sqlserver/SQLSERVER_INCR_MIGRATE').default;
  [TicketTypes.SQLSERVER_MASTER_FAIL_OVER]: typeof import('./sqlserver/SQLSERVER_MASTER_FAIL_OVER').default;
  [TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH]: typeof import('./sqlserver/SQLSERVER_MASTER_SLAVE_SWITCH').default;
  [TicketTypes.SQLSERVER_RESTORE_LOCAL_SLAVE]: typeof import('./sqlserver/SQLSERVER_RESTORE_LOCAL_SLAVE').default;
  [TicketTypes.SQLSERVER_RESTORE_SLAVE]: typeof import('./sqlserver/SQLSERVER_RESTORE_SLAVE').default;
  [TicketTypes.SQLSERVER_ROLLBACK]: typeof import('./sqlserver/SQLSERVER_ROLLBACK').default;
}>();

export const allTicketMap = {
  ...generateCloneDataHandlerMap,
  ...sqlserverTicketModule,
};

export type CloneDataHandlerMap = typeof allTicketMap;

export type CloneDataHandlerMapKeys = keyof CloneDataHandlerMap | keyof typeof sqlserverTicketModule;

export async function generateCloneData<T extends CloneDataHandlerMap>(
  ticketType: T,
  ticketData: TicketModel<unknown>,
) {
  console.log('ticketType: ', ticketType, sqlserverTicketModule);
  return await allTicketMap[ticketType](ticketData);
}
