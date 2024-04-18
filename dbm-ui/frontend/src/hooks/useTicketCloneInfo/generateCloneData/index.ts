import TicketModel from '@services/model/ticket/ticket';

import { TicketTypes } from '@common/const';

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
};

export type CloneDataHandlerMap = typeof generateCloneDataHandlerMap;

export type CloneDataHandlerMapKeys = keyof CloneDataHandlerMap;

export async function generateCloneData<T extends CloneDataHandlerMapKeys>(ticketType: T, ticketData: TicketModel) {
  return (await generateCloneDataHandlerMap[ticketType](ticketData.details)) as ServiceReturnType<
    CloneDataHandlerMap[T]
  >;
}
