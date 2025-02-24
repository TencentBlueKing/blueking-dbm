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

import { TicketTypes } from '@common/const';

// Redis 集群部署
export function generateRedisApplyCloneData(ticketData: TicketModel<Redis.ClusterApply>) {
  const { details } = ticketData;
  return Promise.resolve({
    bk_biz_id: ticketData.bk_biz_id,
    details: {
      bk_cloud_id: details.bk_cloud_id,
      cap_key: details.cap_key,
      city_code: details.city_code,
      cluster_alias: details.cluster_alias,
      cluster_name: details.cluster_name,
      cluster_type: details.cluster_type,
      db_app_abbr: details.db_app_abbr,
      db_version: details.db_version,
      disaster_tolerance_level: details.disaster_tolerance_level,
      ip_source: details.ip_source,
      nodes: details.nodes,
      proxy_port: details.proxy_port,
      proxy_pwd: details.proxy_pwd,
      resource_spec: {
        backend_group: {
          affinity: details.resource_spec.backend_group.affinity,
          capacity: '',
          count: details.resource_spec.backend_group.count,
          future_capacity: '',
          location_spec: details.resource_spec.backend_group.location_spec,
          spec_id: details.resource_spec.backend_group.spec_id,
        },
        proxy: {
          count: details.resource_spec.proxy.count,
          spec_id: details.resource_spec.proxy.spec_id,
        },
      },
    },
    remark: ticketData.remark,
    ticket_type: TicketTypes.REDIS_CLUSTER_APPLY,
  });
}
