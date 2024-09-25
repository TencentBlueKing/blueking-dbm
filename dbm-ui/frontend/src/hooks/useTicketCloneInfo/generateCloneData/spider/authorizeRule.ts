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
import type { MysqlAuthorizationDetails } from '@services/model/ticket/details/mysql';
import TicketModel from '@services/model/ticket/ticket';
import { checkHost } from '@services/source/ipchooser';
import { getTendbClusterList } from '@services/source/tendbcluster';

import { ClusterTypes } from '@common/const';

// Spider 集群授权
export async function generateSpiderAuthorizeRuleCloneData(ticketData: TicketModel<MysqlAuthorizationDetails>) {
  const { authorize_data: authorizeData } = ticketData.details;
  const sourceIpList: ServiceReturnType<typeof checkHost> = [];
  if (authorizeData.source_ips && Array.isArray(authorizeData.source_ips)) {
    const checkIpInfo = await checkHost({
      ip_list: ticketData.details.authorize_data.source_ips!.map((item) => item.ip),
      scope_list: [
        {
          scope_type: 'biz',
          scope_id: ticketData.bk_biz_id,
        },
      ],
    });
    sourceIpList.push(...checkIpInfo);
  }

  const clustersResult = await getTendbClusterList({
    cluster_ids: authorizeData.cluster_ids,
    limit: -1,
    offset: 0,
  });
  const clusterList: {
    master_domain: string;
    cluster_name: string;
  }[] = clustersResult.results;

  return {
    clusterType: authorizeData.cluster_type as ClusterTypes,
    clusterList,
    dbs: authorizeData.access_dbs,
    sourceIpList,
    user: authorizeData.user,
  };
}
