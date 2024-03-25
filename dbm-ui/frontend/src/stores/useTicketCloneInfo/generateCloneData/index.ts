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

const redisOperationTypes = [
  TicketTypes.REDIS_KEYS_EXTRACT,
  TicketTypes.REDIS_KEYS_DELETE,
  TicketTypes.REDIS_BACKUP,
  TicketTypes.REDIS_PURGE,
];

export async function generateCloneData(ticketData: TicketModel<any>) {
  const ticketType = ticketData.ticket_type;

  // Redis 接入层扩容
  if (ticketType === TicketTypes.REDIS_PROXY_SCALE_UP) {
    return await generateRedisProxyScaleUpCloneData(ticketData.details);
  }

  // Redis 接入层缩容
  if (ticketType === TicketTypes.REDIS_PROXY_SCALE_DOWN) {
    return await generateRedisProxyScaleDownCloneData(ticketData.details);
  }

  // Redis 集群容量变更
  if (ticketType === TicketTypes.REDIS_SCALE_UPDOWN) {
    return await generateRedisScaleUpdownCloneData(ticketData.details);
  }

  // Redis 集群分片数变更
  if (ticketType === TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE) {
    return await generateRedisClusterShardUpdateCloneData(ticketData.details);
  }

  // Redis 集群类型变更
  if (ticketType === TicketTypes.REDIS_CLUSTER_TYPE_UPDATE) {
    return await generateRedisClusterTypeUpdateCloneData(ticketData.details);
  }

  // Redis 定点构造
  if (ticketType === TicketTypes.REDIS_DATA_STRUCTURE) {
    return await generateRedisDataStructureCloneData(ticketData.details);
  }

  // Redis 主从切换
  if (ticketType === TicketTypes.REDIS_MASTER_SLAVE_SWITCH) {
    return await generateRedisMasterSlaveSwitchCloneData(ticketData.details);
  }

  // Redis 以构造实例恢复
  if (ticketType === TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY) {
    return generateRedisRollbackDataCloneData(ticketData.details);
  }

  // Redis 集群数据复制
  if (ticketType === TicketTypes.REDIS_CLUSTER_DATA_COPY) {
    return generateRedisDataCopyCloneData(ticketData.details);
  }

  // Redis 数据校验与修复
  if (ticketType === TicketTypes.REDIS_DATACOPY_CHECK_REPAIR) {
    return generateRedisDataCopyCheckRepairCloneData(ticketData.details);
  }

  // Redis 重建从库
  if (ticketType === TicketTypes.REDIS_CLUSTER_ADD_SLAVE) {
    return await generateRedisClusterAddSlaveCloneData(ticketData.details);
  }

  // Redis 整机替换
  if (ticketType === TicketTypes.REDIS_CLUSTER_CUTOFF) {
    return generateRedisClusterCutoffCloneData(ticketData.details);
  }

  // Redis 提取Key/删除Key/集群备份/集群清档
  if (redisOperationTypes.includes(ticketType)) {
    return generateRedisOperationCloneData(ticketData.details);
  }
}
