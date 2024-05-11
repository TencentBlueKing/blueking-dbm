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

import type { SpiderMNTApplyDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';

import { random } from '@utils';

// Spider 临时节点添加
export function generateSpiderAddMntDataCloneData(ticketData: TicketModel<SpiderMNTApplyDetails>) {
  const { infos, clusters } = ticketData.details;
  const tableDataList = infos.map((item) => ({
    rowKey: random(),
    clusterData: {
      id: clusters[item.cluster_id].id,
      domain: clusters[item.cluster_id].immute_domain,
    },
    bkCloudId: clusters[item.cluster_id].bk_cloud_id,
    spiderIpList: item.spider_ip_list,
  }));

  return Promise.resolve({
    tableDataList,
    remark: ticketData.remark,
  });
}
