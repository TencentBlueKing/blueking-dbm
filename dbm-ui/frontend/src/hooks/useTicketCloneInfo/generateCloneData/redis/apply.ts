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
    ticket_type: TicketTypes.REDIS_CLUSTER_APPLY,
    remark: ticketData.remark,
    details: {
      bk_cloud_id: details.bk_cloud_id,
      db_app_abbr: details.db_app_abbr,
      proxy_port: details.proxy_port,
      cluster_name: details.cluster_name,
      cluster_alias: details.cluster_alias,
      cluster_type: details.cluster_type,
      city_code: details.city_code,
      db_version: details.db_version,
      cap_key: details.cap_key,
      ip_source: details.ip_source,
      disaster_tolerance_level: details.disaster_tolerance_level,
      proxy_pwd: details.proxy_pwd,
      nodes: details.nodes,
      resource_spec: {
        proxy: {
          spec_id: details.resource_spec.proxy.spec_id,
          count: details.resource_spec.proxy.count,
        },
        backend_group: {
          count: details.resource_spec.backend_group.count,
          spec_id: details.resource_spec.backend_group.spec_id,
          capacity: '',
          future_capacity: '',
          affinity: details.resource_spec.backend_group.affinity,
          location_spec: details.resource_spec.backend_group.location_spec,
        },
      },
    },
  });
}
