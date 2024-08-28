/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
import type { RedisAddSlaveDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { getRedisMachineList } from '@services/source/redis';

import { random } from '@utils';

// Redis 重建从库
export async function generateRedisClusterAddSlaveCloneData(ticketData: TicketModel<RedisAddSlaveDetails>) {
  const { infos } = ticketData.details;
  const masterIps: string[] = [];
  const masterSlaveIpMap: Record<string, string> = {};
  const IpInfoMap: Record<
    string,
    {
      cluster_ids: number[];
      bk_cloud_id: number;
      bk_host_id: number;
    }
  > = {};
  infos.forEach((item) => {
    item.pairs.forEach((pair) => {
      const masterIp = pair.redis_master.ip;
      masterSlaveIpMap[masterIp] = pair.redis_slave.old_slave_ip;
      masterIps.push(masterIp);
      IpInfoMap[masterIp] = {
        cluster_ids: item.cluster_ids,
        bk_cloud_id: pair.redis_master.bk_cloud_id,
        bk_host_id: pair.redis_master.bk_host_id,
      };
    });
  });
  const listResult = await getRedisMachineList({
    ip: masterIps.join(','),
    add_role_count: true,
  });
  const machineIpMap = listResult.results.reduce(
    (results, item) => {
      Object.assign(results, {
        [item.ip]: item,
      });
      return results;
    },
    {} as Record<string, ServiceReturnType<typeof getRedisMachineList>['results'][number]>,
  );

  return {
    tableDataList: masterIps.map((ip) => ({
      rowKey: random(),
      isLoading: false,
      slaveIp: masterSlaveIpMap[ip],
      masterIp: ip,
      ip,
      clusterIds: IpInfoMap[ip].cluster_ids,
      bkCloudId: IpInfoMap[ip].bk_cloud_id,
      bkHostId: IpInfoMap[ip].bk_host_id,
      cluster: {
        domain: machineIpMap[ip].related_clusters.map((item) => item.immute_domain).join(','),
        isStart: false,
        isGeneral: true,
        rowSpan: 1,
      },
      spec: machineIpMap[ip].spec_config,
      targetNum: 1,
      slaveHost: {
        faults: machineIpMap[ip].unavailable_slave,
        total: machineIpMap[ip].total_slave,
      },
    })),
    remark: ticketData.remark,
  };
}
