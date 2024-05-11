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

import type { SpiderApplyDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';

// spider 集群部署
export async function generateSpiderApplyCloneData(ticketData: TicketModel<SpiderApplyDetails>) {
  const { details } = ticketData;

  return Promise.resolve({
    bizId: ticketData.bk_biz_id,
    affinity: details.disaster_tolerance_level,
    cloudId: details.bk_cloud_id,
    cityCode: details.city_code,
    dbModuleId: details.db_module_id,
    remark: ticketData.remark,
    clusterName: details.cluster_name,
    clusterAlias: details.cluster_alias,
    spiderPort: details.spider_port,
    spiderSpecId: details.resource_spec.spider.spec_id,
    spiderSpecCount: details.resource_spec.spider.count,
    backendSpecId: details.resource_spec.backend_group.spec_id,
    backendSpecCount: details.resource_spec.backend_group.spec_id,
    capacity: details.resource_spec.backend_group.capacity,
    futureCapacity: details.resource_spec.backend_group.future_capacity,
  });
}
