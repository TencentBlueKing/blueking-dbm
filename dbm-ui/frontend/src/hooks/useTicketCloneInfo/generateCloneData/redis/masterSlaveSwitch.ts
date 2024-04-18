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
import { queryMasterSlaveByIp } from '@services/source/redisToolbox';

import { random } from '@utils';

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
