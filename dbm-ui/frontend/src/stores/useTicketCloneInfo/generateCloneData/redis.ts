import RedisModel from '@services/model/redis/redis';
import { getRedisList } from '@services/source/redis';
import { queryInfoByIp, queryMasterSlaveByIp } from '@services/source/redisToolbox';

import type { RedisAddSlaveDetails } from '@views/tickets/common/components/demand-factory/redis/AddSlave.vue';
import type { RedisScaleUpDownDetails } from '@views/tickets/common/components/demand-factory/redis/ClusterCapacityUpdate.vue';
import type { RedisClusterShardUpdateDetails } from '@views/tickets/common/components/demand-factory/redis/ClusterShardUpdate.vue';
import type { RedisClusterTypeUpdateDetails } from '@views/tickets/common/components/demand-factory/redis/ClusterTypeUpdate.vue';
import type { RedisDataCheckAndRepairDetails } from '@views/tickets/common/components/demand-factory/redis/DataCheckAndRepair.vue';
import type { RedisDataCopyDetails } from '@views/tickets/common/components/demand-factory/redis/DataCopy.vue';
import type { RedisDataStructrueDetails } from '@views/tickets/common/components/demand-factory/redis/DataStructure.vue';
import type { RedisDBReplaceDetails } from '@views/tickets/common/components/demand-factory/redis/DBReplace.vue';
import type { RedisMasterSlaveSwitchDetails } from '@views/tickets/common/components/demand-factory/redis/MasterFailover.vue';
import type { RedisKeysDetails } from '@views/tickets/common/components/demand-factory/redis/Operation.vue';
import type { RedisProxyScaleDownDetails } from '@views/tickets/common/components/demand-factory/redis/ProxyScaleDown.vue';
import type { RedisProxyScaleUpDetails } from '@views/tickets/common/components/demand-factory/redis/ProxyScaleUp.vue';
import type { RedisRollbackDataCopyDetails } from '@views/tickets/common/components/demand-factory/redis/RollbackDataCopy.vue';

import { random } from '@utils';

import { t } from '@locales/index';

// Redis 接入层扩容
export async function generateRedisProxyScaleUpCloneData(details: RedisProxyScaleUpDetails) {
  const { clusters, infos, specs } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.cluster_id).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  return infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    cluster: clusters[item.cluster_id].immute_domain,
    clusterId: item.cluster_id,
    bkCloudId: item.bk_cloud_id,
    nodeType: 'Proxy',
    targetNum: item.target_proxy_count,
    spec: {
      ...specs[item.resource_spec.proxy.spec_id],
      count: clusterListMap[item.cluster_id].proxy.length,
    },
    rowModelData: clusterListMap[item.cluster_id],
  }));
}

// Redis 接入层缩容
export async function generateRedisProxyScaleDownCloneData(details: RedisProxyScaleDownDetails) {
  const { clusters, infos } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.cluster_id).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  return infos.map((item) => {
    const clusterId = item.cluster_id;
    return {
      rowKey: random(),
      isLoading: false,
      cluster: clusters[clusterId].immute_domain,
      clusterId,
      bkCloudId: clusterListMap[clusterId].bk_cloud_id,
      nodeType: 'Proxy',
      spec: {
        ...clusterListMap[clusterId].proxy[0].spec_config,
        name: clusterListMap[clusterId].cluster_spec.spec_name,
        id: clusterListMap[clusterId].cluster_spec.spec_id,
        count: clusterListMap[clusterId].proxy.length,
      },
      targetNum: `${clusterListMap[clusterId].proxy.length}`,
    };
  });
}

// Redis 集群容量变更
export async function generateRedisScaleUpdownCloneData(details: RedisScaleUpDownDetails) {
  const { clusters, infos } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.cluster_id).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  return infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    targetCluster: clusters[item.cluster_id].immute_domain,
    currentSepc: clusterListMap[item.cluster_id].cluster_spec.spec_name,
    clusterId: item.cluster_id,
    bkCloudId: item.bk_cloud_id,
    shardNum: item.shard_num,
    groupNum: item.group_num,
    version: item.db_version,
    clusterType: clusters[item.cluster_id].cluster_type,
    currentCapacity: {
      used: 1,
      total: clusterListMap[item.cluster_id].cluster_capacity,
    },
    switchMode: item.online_switch_type,
  }));
}

// Redis 集群分片数变更
export async function generateRedisClusterShardUpdateCloneData(details: RedisClusterShardUpdateDetails) {
  const { clusters, infos } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.src_cluster).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  const tableData = infos.map((item) => {
    const currentClusterInfo = clusterListMap[item.src_cluster];
    return {
      rowKey: random(),
      isLoading: false,
      srcCluster: clusters[item.src_cluster].immute_domain,
      clusterId: item.src_cluster,
      bkCloudId: currentClusterInfo.bk_cloud_id,
      switchMode: t('需人工确认'),
      currentCapacity: {
        used: 1,
        total: currentClusterInfo.cluster_capacity,
      },
      currentSepc: `${currentClusterInfo.cluster_capacity}G_${currentClusterInfo.cluster_spec.qps.max}/s（${currentClusterInfo.cluster_shard_num} 分片）`,
      clusterType: currentClusterInfo.cluster_spec.spec_cluster_type,
      currentShardNum: currentClusterInfo.cluster_shard_num,
      currentSpecId: currentClusterInfo.cluster_spec.spec_id,
      dbVersion: item.db_version,
      specConfig: {
        cpu: currentClusterInfo.cluster_spec.cpu,
        id: currentClusterInfo.cluster_spec.spec_id,
        mem: currentClusterInfo.cluster_spec.mem,
        qps: currentClusterInfo.cluster_spec.qps,
      },
      proxy: {
        id: currentClusterInfo.proxy[0].spec_config.id,
        count: new Set(currentClusterInfo.proxy.map((item) => item.ip)).size,
      },
    };
  });
  return {
    tableList: tableData,
    type: details.data_check_repair_setting.type,
    frequency: details.data_check_repair_setting.execution_frequency,
  };
}

// Redis 集群类型变更
export async function generateRedisClusterTypeUpdateCloneData(details: RedisClusterTypeUpdateDetails) {
  const { clusters, infos } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.src_cluster).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  const tableData = infos.map((item) => {
    const currentClusterInfo = clusterListMap[item.src_cluster];
    return {
      rowKey: random(),
      isLoading: false,
      srcCluster: clusters[item.src_cluster].immute_domain,
      srcClusterType: currentClusterInfo.cluster_type_name,
      clusterType: currentClusterInfo.cluster_type,
      clusterId: item.src_cluster,
      bkCloudId: currentClusterInfo.bk_cloud_id,
      switchMode: t('需人工确认'),
      currentCapacity: {
        used: 1,
        total: currentClusterInfo.cluster_capacity,
      },
      currentSepc: `${currentClusterInfo.cluster_capacity}G_${currentClusterInfo.cluster_spec.qps.max}/s${t('（n 分片）', { n: currentClusterInfo.cluster_shard_num })}`,
      targetClusterType: item.target_cluster_type,
      currentShardNum: currentClusterInfo.cluster_shard_num,
      currentSpecId: currentClusterInfo.cluster_spec.spec_id,
      dbVersion: item.db_version,
      specConfig: {
        cpu: currentClusterInfo.cluster_spec.cpu,
        id: currentClusterInfo.cluster_spec.spec_id,
        mem: currentClusterInfo.cluster_spec.mem,
        qps: currentClusterInfo.cluster_spec.qps,
      },
      proxy: {
        id: currentClusterInfo.proxy[0].spec_config.id,
        count: new Set(currentClusterInfo.proxy.map((item) => item.ip)).size,
      },
    };
  });
  return {
    tableList: tableData,
    type: details.data_check_repair_setting.type,
    frequency: details.data_check_repair_setting.execution_frequency,
  };
}

// Redis 定点构造
export async function generateRedisDataStructureCloneData(details: RedisDataStructrueDetails) {
  const { infos } = details;
  const clusterListResult = await getRedisList({
    cluster_ids: infos.map((item) => item.cluster_id).join(','),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, RedisModel>,
  );

  return infos.map((item) => {
    const currentClusterInfo = clusterListMap[item.cluster_id];
    const instances = currentClusterInfo.redis_master.map((row) => `${row.ip}:${row.port}`);
    return {
      rowKey: currentClusterInfo.master_domain,
      isLoading: false,
      cluster: currentClusterInfo.master_domain,
      clusterType: currentClusterInfo.cluster_type,
      clusterId: item.cluster_id,
      bkCloudId: item.bk_cloud_id,
      hostNum: item.resource_spec.redis.count,
      targetDateTime: item.recovery_time_point,
      instances,
      spec: {
        ...currentClusterInfo.cluster_spec,
        name: currentClusterInfo.cluster_spec.spec_name,
        id: currentClusterInfo.cluster_spec.spec_id,
      },
    };
  });
}

// Redis 以构造实例恢复
export function generateRedisRollbackDataCloneData(details: RedisRollbackDataCopyDetails) {
  const { clusters, infos } = details;
  const tableList = infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: item.src_cluster,
    targetTime: item.recovery_time_point,
    targetCluster: clusters[item.dst_cluster].immute_domain,
    targetClusterId: item.dst_cluster,
    includeKey: item.key_white_regex ? item.key_white_regex.split(',') : [],
    excludeKey: item.key_black_regex ? item.key_black_regex.split(',') : [],
  }));

  return {
    tableList,
    writeMode: details.write_mode,
  };
}

// Redis 集群数据复制
export function generateRedisDataCopyCloneData(details: RedisDataCopyDetails) {
  const { clusters, infos } = details;

  const tableList = infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    srcCluster:
      details.dts_copy_type === 'user_built_to_dbm' ? item.src_cluster : clusters[item.src_cluster]?.immute_domain,
    srcClusterId: item.src_cluster,
    clusterType: item.src_cluster_type,
    targetCluster:
      details.dts_copy_type === 'copy_to_other_system' ? item.dst_cluster : clusters[item.dst_cluster]?.immute_domain,
    targetClusterId: item.dst_cluster,
    includeKey: item.key_white_regex ? item.key_white_regex.split(',') : [],
    excludeKey: item.key_black_regex ? item.key_black_regex.split(',') : [],
    targetBusines: item.dst_bk_biz_id,
    password: item.src_cluster_password,
  }));

  return {
    tableList,
    copyMode: details.dts_copy_type,
    writeMode: details.write_mode,
    disconnectSetting: details.sync_disconnect_setting,
  };
}

// Redis 数据校验与修复
export function generateRedisDataCopyCheckRepairCloneData(details: RedisDataCheckAndRepairDetails) {
  const tableList = details.infos.map((item) => ({
    rowKey: random(),
    isLoading: false,
    billId: item.bill_id,
    srcCluster: item.src_cluster,
    targetCluster: item.dst_cluster,
    relateTicket: item.bill_id,
    instances: t('全部'),
    includeKey: item.key_white_regex ? item.key_white_regex.split(',') : [],
    excludeKey: item.key_black_regex ? item.key_black_regex.split(',') : [],
  }));

  return {
    tableList,
    executeType: details.execute_mode,
    executeTime: details.specified_execution_time,
    stopTime: details.check_stop_time,
    isKeepCheck: details.keep_check_and_repair,
    isRepairEnable: details.data_repair_enabled,
    repairType: details.repair_mode,
  };
}

// Redis 主从切换
export async function generateRedisMasterSlaveSwitchCloneData(details: RedisMasterSlaveSwitchDetails) {
  const { infos, force } = details;
  const ips: string[] = [];
  const ipSwitchMode: Record<string, string> = {};
  infos.forEach((item) => {
    item.pairs.forEach((pair) => {
      const masterIp = pair.redis_master;
      ips.push(masterIp);
      ipSwitchMode[masterIp] = item.online_switch_type;
    });
  });
  const result = await queryMasterSlaveByIp({ ips });
  const masterIpMap = result.reduce(
    (results, item) => {
      Object.assign(results, {
        [item.master_ip]: item,
      });
      return results;
    },
    {} as Record<string, any>,
  );
  const tableList = ips.map((ip) => ({
    rowKey: random(),
    isLoading: false,
    ip,
    clusterId: masterIpMap[ip].cluster.id,
    cluster: masterIpMap[ip].cluster.immute_domain,
    masters: masterIpMap[ip].instances.map((item: { instance: string }) => item.instance),
    slave: masterIpMap[ip].slave_ip,
    switchMode: ipSwitchMode[ip],
  }));
  return {
    tableList,
    force,
  };
}

// Redis 重建从库
export async function generateRedisClusterAddSlaveCloneData(details: RedisAddSlaveDetails) {
  const { infos } = details;
  const ips: string[] = [];
  const IpInfoMap: Record<
    string,
    {
      cluster_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
    }
  > = {};
  infos.forEach((item) => {
    item.pairs.forEach((pair) => {
      const masterIp = pair.redis_master.ip;
      ips.push(masterIp);
      IpInfoMap[masterIp] = {
        cluster_id: item.cluster_id,
        bk_cloud_id: pair.redis_master.bk_cloud_id,
        bk_host_id: pair.redis_master.bk_host_id,
      };
    });
  });
  const infoResult = await queryInfoByIp({ ips });
  const infoMap = infoResult.reduce(
    (results, item) => {
      Object.assign(results, {
        [item.ip]: item,
      });
      return results;
    },
    {} as Record<string, any>,
  );

  return ips.map((ip) => ({
    rowKey: random(),
    isLoading: false,
    ip,
    clusterId: IpInfoMap[ip].cluster_id,
    bkCloudId: IpInfoMap[ip].bk_cloud_id,
    bkHostId: IpInfoMap[ip].bk_host_id,
    slaveNum: infoMap[ip].cluster.redis_slave_count,
    cluster: {
      domain: infoMap[ip].cluster.immute_domain,
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
    spec: infoMap[ip].spec_config,
    targetNum: 1,
    slaveHost: {
      faults: infoMap[ip].unavailable_slave,
      total: infoMap[ip].total_slave,
    },
  }));
}

// Redis 整机替换
export function generateRedisClusterCutoffCloneData(details: RedisDBReplaceDetails) {
  const { clusters, infos, specs } = details;
  return infos.reduce((dataList, item) => {
    const roleList = ['proxy', 'redis_master', 'redis_slave'] as ['proxy', 'redis_master', 'redis_slave'];
    const roleMap = {
      redis_master: 'master',
      redis_slave: 'slave',
      proxy: 'proxy',
    };
    roleList.forEach((role) => {
      if (item[role].length > 0) {
        item[role].forEach((info) => {
          dataList.push({
            rowKey: random(),
            isLoading: false,
            ip: info.ip,
            role: roleMap[role],
            clusterId: item.cluster_id,
            bkCloudId: item.bk_cloud_id,
            cluster: {
              domain: clusters[item.cluster_id].immute_domain,
              isStart: false,
              isGeneral: true,
              rowSpan: 1,
            },
            spec: specs[info.spec_id],
          });
        });
      }
    });
    return dataList;
  }, [] as any[]);
}

// Redis 提取Key/删除Key/备份
export function generateRedisOperationCloneData(details: RedisKeysDetails) {
  const { clusters, rules } = details;
  return rules.map((item) => ({
    ...clusters[item.cluster_id],
    ...item,
    master_domain: clusters[item.cluster_id].immute_domain,
  }));
}
