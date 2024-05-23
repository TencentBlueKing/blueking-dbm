import TicketModel from '@services/model/ticket/ticket';

import { TicketTypes } from '@common/const';

import {
  generateMysqlAuthorizeRuleCloneData,
  generateMysqlChecksumCloneData,
  generateMysqlClientCloneData,
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
  generateMysqlProxyAddCloneData,
  generateMysqlProxyReplaceCloneData,
  generateMysqlRestoreLocalSlaveCloneData,
  generateMysqlRestoreSlaveCloneData,
  generateMysqlRollbackCloneData,
  generateMysqlSingleApplyCloneData,
  generateMysqlSlaveAddCloneData,
} from './mysql';
import {
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
  generateRedisRollbackDataCloneData,
  generateRedisScaleUpdownCloneData,
} from './redis';

export const generateCloneDataHandlerMap = {
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
  [TicketTypes.MYSQL_SINGLE_APPLY] : generateMysqlSingleApplyCloneData, // MySQL 单节点部署
  [TicketTypes.MYSQL_HA_DB_TABLE_BACKUP]: generateMysqlDbTableBackupCloneData, // Mysql 库表备份
  [TicketTypes.MYSQL_HA_RENAME_DATABASE]: generateMysqlDbRenameCloneData,// MySQL 高可用DB重命名
  [TicketTypes.MYSQL_HA_FULL_BACKUP]: generateMysqlDbBackupCloneData, // Mysql 全库备份
  [TicketTypes.MYSQL_ROLLBACK_CLUSTER]: generateMysqlRollbackCloneData, // MySQL 定点构造
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
};

export type CloneDataHandlerMap = typeof generateCloneDataHandlerMap;

export type CloneDataHandlerMapKeys = keyof CloneDataHandlerMap;

export async function generateCloneData<T extends CloneDataHandlerMapKeys>(ticketType: T, ticketData: TicketModel) {
  return (await generateCloneDataHandlerMap[ticketType](ticketData)) as ServiceReturnType<
    CloneDataHandlerMap[T]
  >;
}
