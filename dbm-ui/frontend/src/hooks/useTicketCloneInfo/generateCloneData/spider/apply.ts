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

import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

// spider 集群部署
export async function generateSpiderApplyCloneData(ticketData: TicketModel<TendbCluster.Apply>) {
  const { details } = ticketData;

  return Promise.resolve({
    affinity: details.disaster_tolerance_level,
    backendSpecCount: details.resource_spec.backend_group.spec_id,
    backendSpecId: details.resource_spec.backend_group.spec_id,
    bizId: ticketData.bk_biz_id,
    capacity: details.resource_spec.backend_group.capacity,
    cityCode: details.city_code,
    cloudId: details.bk_cloud_id,
    clusterAlias: details.cluster_alias,
    clusterName: details.cluster_name,
    dbModuleId: details.db_module_id,
    futureCapacity: details.resource_spec.backend_group.future_capacity,
    remark: ticketData.remark,
    spiderPort: details.spider_port,
    spiderSpecCount: details.resource_spec.spider.count,
    spiderSpecId: details.resource_spec.spider.spec_id,
  });
}
