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
import type { RedisMasterSlaveSwitchDetails } from '@services/model/ticket/details/redis';
import TicketModel from '@services/model/ticket/ticket';
import { checkRedisInstances } from '@services/source/instances';
import { queryMachineInstancePair } from '@services/source/redisToolbox';

import { random } from '@utils';

// Redis 主从切换
export async function generateRedisMasterSlaveSwitchCloneData(ticketData: TicketModel<RedisMasterSlaveSwitchDetails>) {
  const { infos, force } = ticketData.details;
  const masterIps: string[] = [];
  const ipSwitchMode: Record<string, string> = {};
  infos.forEach((item) => {
    item.pairs.forEach((pair) => {
      const masterIp = pair.redis_master;
      masterIps.push(masterIp);
      ipSwitchMode[masterIp] = item.online_switch_type;
    });
  });

  const checkResult = await checkRedisInstances({
    bizId: ticketData.bk_biz_id,
    instance_addresses: masterIps,
  });

  const ipInfo = Array.from(new Set(checkResult.map((item) => `${item.bk_cloud_id}:${item.ip}`)));
  const pairResult = await queryMachineInstancePair({ machines: ipInfo });
  const masterIpMap = pairResult.machines!;

  const tableList = ipInfo.map((key) => {
    const ip = key.split(':')[1];
    return {
      rowKey: random(),
      isLoading: false,
      ip,
      clusterIds: masterIpMap[key].related_clusters.map((item) => item.id),
      clusters: masterIpMap[key].related_clusters.map((item) => item.immute_domain),
      masters: masterIpMap[key].related_pair_instances.map((item) => item.instance),
      slave: masterIpMap[key].ip,
      switchMode: ipSwitchMode[ip],
    };
  });
  return {
    tableList,
    force,
    remark: ticketData.remark,
  };
}
