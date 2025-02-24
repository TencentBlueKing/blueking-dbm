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
import TicketModel, { type Redis } from '@services/model/ticket/ticket';
import { getRedisMachineList } from '@services/source/redis';

import { random } from '@utils';

// Redis 重建从库
export async function generateRedisClusterAddSlaveCloneData(ticketData: TicketModel<Redis.ClusterAddSlave>) {
  const { infos } = ticketData.details;
  const masterIps: string[] = [];
  const masterSlaveIpMap: Record<string, string> = {};
  const IpInfoMap: Record<
    string,
    {
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_ids: number[];
    }
  > = {};
  infos.forEach((item) => {
    item.pairs.forEach((pair) => {
      const masterIp = pair.redis_master.ip;
      masterSlaveIpMap[masterIp] = pair.redis_slave.old_slave_ip;
      masterIps.push(masterIp);
      IpInfoMap[masterIp] = {
        bk_cloud_id: pair.redis_master.bk_cloud_id,
        bk_host_id: pair.redis_master.bk_host_id,
        cluster_ids: item.cluster_ids,
      };
    });
  });
  const listResult = await getRedisMachineList({
    add_role_count: true,
    ip: masterIps.join(','),
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
    remark: ticketData.remark,
    tableDataList: masterIps.map((ip) => ({
      bkCloudId: IpInfoMap[ip].bk_cloud_id,
      bkHostId: IpInfoMap[ip].bk_host_id,
      cluster: {
        domain: machineIpMap[ip].related_clusters.map((item) => item.immute_domain).join(','),
        isGeneral: true,
        isStart: false,
        rowSpan: 1,
      },
      clusterIds: IpInfoMap[ip].cluster_ids,
      ip,
      isLoading: false,
      masterIp: ip,
      rowKey: random(),
      slaveIp: masterSlaveIpMap[ip],
      spec: machineIpMap[ip].spec_config,
      targetNum: 1,
    })),
  };
}
