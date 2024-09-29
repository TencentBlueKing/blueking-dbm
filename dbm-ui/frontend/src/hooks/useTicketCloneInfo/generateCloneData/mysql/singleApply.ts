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
import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

// Mysql 单节点部署
export function generateMysqlSingleApplyCloneData(ticketData: TicketModel<Mysql.SingleApply>) {
  const { details } = ticketData;
  return Promise.resolve({
    affinity: details.disaster_tolerance_level,
    bizId: ticketData.bk_biz_id,
    cloudId: details.bk_cloud_id,
    cityCode: details.city_code,
    clusterCount: details.cluster_count,
    dbModuleId: details.db_module_id,
    dbAppAbbr: ticketData.db_app_abbr,
    domains: details.domains,
    instNum: details.inst_num,
    ipSource: details.ip_source,
    nodes: details.nodes,
    singleSpecId: details.resource_spec?.backend.spec_id,
    remark: ticketData.remark,
    startMysqlPort: details.start_mysql_port,
  });
}
