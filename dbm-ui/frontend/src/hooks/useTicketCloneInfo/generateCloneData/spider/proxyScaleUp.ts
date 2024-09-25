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

import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
import type { SpiderAddNodesDeatils } from '@services/model/ticket/details/spider';
import TicketModel from '@services/model/ticket/ticket';
import { getTendbClusterList } from '@services/source/tendbcluster';

import { random } from '@utils';

// spider扩容接入层
export async function generateSpiderProxyScaleUpCloneData(ticketData: TicketModel<SpiderAddNodesDeatils>) {
  const { infos } = ticketData.details;
  const clusterListResult = await getTendbClusterList({
    cluster_ids: infos.map((item) => item.cluster_id),
  });
  const clusterListMap = clusterListResult.results.reduce<Record<number, TendbclusterModel>>((obj, item) => {
    Object.assign(obj, {
      [item.id]: item,
    });
    return obj;
  }, {});

  const tableDataList = infos.map((item) => {
    const clusterItem = clusterListMap[item.cluster_id];
    const masterCount = clusterItem.spider_master.length;
    const slaveCount = clusterItem.spider_slave.length;
    // const nodeCount = item.resource_spec.spider_ip_list.count;
    // let targetNum = 0;

    // if (item.add_spider_role === 'spider_master') {
    //   targetNum = nodeCount + masterCount;
    // } else {
    //   targetNum = nodeCount + slaveCount;
    // }

    return {
      rowKey: random(),
      isLoading: false,
      cluster: clusterItem.master_domain,
      clusterId: item.cluster_id,
      bkCloudId: clusterItem.bk_cloud_id,
      nodeType: item.add_spider_role,
      masterCount,
      slaveCount,
      mntCount: clusterItem.spider_mnt.length,
      spiderMasterList: clusterItem.spider_master,
      spiderSlaveList: clusterItem.spider_slave,
      // spec: {
      //   ...clusterItem.spider_master[0].spec_config,
      //   count: targetNum,
      // },
      specId: item.resource_spec.spider_ip_list.spec_id,
      targetNum: String(item.resource_spec.spider_ip_list.count),
      clusterType: clusterItem.cluster_spec.spec_cluster_type,
    };
  });

  return {
    tableDataList,
    remark: ticketData.remark,
  };
}
