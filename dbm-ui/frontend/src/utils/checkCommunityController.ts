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
import { useFunController } from '@stores';

import { TicketTypes } from '@common/const';

// community 统一控制功能键和单据类型，不影响其他数据库和热 Key 分析。
const controlledFeatures = new Set<string>([
  'mysql.clb',
  'mysql.toolbox.dtsDataMigrate',
  'redis.clb',
  'redis.clusterManage.DNSDomainToCLB',
  'redis.clusterManage.enableCLB',
  'redis.toolbox.dataCopy',
  'redis.toolbox.dataCopyRecord',
  'redis.toolbox.recoverFromInstance',
  'redis.toolbox.memoryAnalysis',
  'redis.toolbox.memoryAnalysisList',
]);

const controlledTicketTypes = new Set<string>([
  TicketTypes.MYSQL_DTS_DATA_MIGRATE,
  TicketTypes.MYSQL_DTS_DATA_MIGRATE_RENAME,
  TicketTypes.MYSQL_ADD_CLB,
  TicketTypes.MYSQL_CLB_BIND_DOMAIN,
  TicketTypes.MYSQL_CLB_UNBIND_DOMAIN,
  TicketTypes.REDIS_CLUSTER_DATA_COPY,
  TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
  TicketTypes.REDIS_DATACOPY_CHECK_REPAIR,
  TicketTypes.REDIS_PLUGIN_CREATE_CLB,
  TicketTypes.REDIS_PLUGIN_DELETE_CLB,
  TicketTypes.REDIS_PLUGIN_DNS_BIND_CLB,
  TicketTypes.REDIS_PLUGIN_DNS_UNBIND_CLB,
  TicketTypes.REDIS_KEYSTAT,
]);

export function checkCommunityController(key: string) {
  if (!controlledFeatures.has(key) && !controlledTicketTypes.has(key)) {
    return true;
  }

  const { funControllerData } = useFunController();
  // 显式启用社区版限制时排除指定功能和单据，未配置时保持原有行为。
  return funControllerData.community?.is_enabled !== true;
}
