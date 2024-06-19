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

import SpiderModel from '@services/model/spider/spider';
import type { SpiderReduceNodesDetails } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';
import { getSpiderList } from '@services/source/spider';

import { random } from '@utils';

// spider 缩容接入层
export async function generateSpiderProxyScaleDownCloneData(ticketData: TicketModel<SpiderReduceNodesDetails>) {
  const { infos, is_safe: isSafe } = ticketData.details;
  const clusterListResult = await getSpiderList({
    cluster_ids: infos.map((item) => item.cluster_id),
  });
  const clusterListMap = clusterListResult.results.reduce(
    (obj, item) => {
      Object.assign(obj, {
        [item.id]: item,
      });
      return obj;
    },
    {} as Record<number, SpiderModel>,
  );

  const tableDataList = infos.map((item) => {
    const clusterItem = clusterListMap[item.cluster_id];
    const masterCount = clusterItem.spider_master.length;
    const slaveCount = clusterItem.spider_slave.length;
    const targetNum = item.spider_reduced_to_count;

    return {
      rowKey: random(),
      isLoading: false,
      cluster: clusterItem.cluster_name,
      clusterId: item.cluster_id,
      bkCloudId: clusterItem.bk_cloud_id,
      nodeType: item.reduce_spider_role,
      masterCount,
      slaveCount,
      mntCount: clusterItem.spider_mnt.length,
      spiderMasterList: clusterItem.spider_master,
      spiderSlaveList: clusterItem.spider_slave,
      spec: {
        ...clusterItem.spider_master[0].spec_config,
        count: targetNum,
      },
      targetNum: String(targetNum),
    };
  });

  return Promise.resolve({
    tableDataList,
    isSafe,
    remark: ticketData.remark,
  });
}