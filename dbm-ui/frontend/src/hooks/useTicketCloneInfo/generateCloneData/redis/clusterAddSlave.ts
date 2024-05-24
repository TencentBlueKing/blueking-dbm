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
import { queryInfoByIp } from '@services/source/redisToolbox';

import { random } from '@utils';

// Redis 重建从库
export async function generateRedisClusterAddSlaveCloneData(ticketData: TicketModel<RedisAddSlaveDetails>) {
  const { infos } = ticketData.details;
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

  return {
    tableDataList: ips.map((ip) => ({
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
    })),
    remark: ticketData.remark,
  };
}
