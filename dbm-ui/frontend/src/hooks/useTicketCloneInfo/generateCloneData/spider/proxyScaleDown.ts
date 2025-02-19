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

import _ from 'lodash';

import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
import { getTendbclusterInstanceList, getTendbClusterList } from '@services/source/tendbcluster';

import { random } from '@utils';

// spider 缩容接入层
export async function generateSpiderProxyScaleDownCloneData(ticketData: TicketModel<TendbCluster.SpiderReduceNodes>) {
  const { infos, is_safe: isSafe } = ticketData.details;
  const [clusterListResult, instanceListResult] = await Promise.all([
    getTendbClusterList({
      cluster_ids: infos.map((item) => item.cluster_id),
    }),
    getTendbclusterInstanceList({
      ip: _.flatten(infos.map((infoItem) => infoItem.spider_reduced_hosts?.map((hostItem) => hostItem.ip))).join(','),
    }),
  ]);
  const clusterListMap = clusterListResult.results.reduce<Record<number, TendbclusterModel>>((obj, item) => {
    Object.assign(obj, {
      [item.id]: item,
    });
    return obj;
  }, {});
  const instanceListMap = instanceListResult.results.reduce<Record<string, TendbclusterInstanceModel>>((obj, item) => {
    Object.assign(obj, {
      [item.ip]: item,
    });
    return obj;
  }, {});

  const formatValue = (data: TendbclusterInstanceModel) => ({
    bk_cloud_id: data?.host_info?.cloud_id || 0,
    bk_cloud_name: data.bk_cloud_name,
    bk_host_id: data.bk_host_id,
    cluster_id: data.cluster_id,
    cluster_type: data.cluster_type,
    db_module_id: data.db_module_id,
    db_module_name: data.db_module_name,
    id: data.id,
    instance_address: data.instance_address || '',
    ip: data.ip || '',
    master_domain: data.master_domain,
    port: data.port,
  });

  const tableDataList = infos.map((item) => {
    const clusterItem = clusterListMap[item.cluster_id];
    const masterCount = clusterItem.spider_master.length;
    const slaveCount = clusterItem.spider_slave.length;
    const nodeList = item.reduce_spider_role === 'spider_master' ? clusterItem.spider_master : clusterItem.spider_slave;
    const targetNum = item.spider_reduced_to_count;

    return {
      bkCloudId: clusterItem.bk_cloud_id,
      cluster: clusterItem.master_domain,
      clusterId: item.cluster_id,
      isLoading: false,
      masterCount,
      mntCount: clusterItem.spider_mnt.length,
      nodeType: item.reduce_spider_role,
      rowKey: random(),
      selectedNodeList: (item.spider_reduced_hosts || []).map((proxyHost) =>
        formatValue(instanceListMap[proxyHost.ip]),
      ),
      slaveCount,
      spec: {
        ...clusterItem.spider_master[0].spec_config,
        count: targetNum,
      },
      spiderMasterList: clusterItem.spider_master,
      spiderSlaveList: clusterItem.spider_slave,
      targetNum: `${nodeList.length - (item.spider_reduced_to_count || 0)}`,
      // targetNum: String(targetNum),
    };
  });

  return Promise.resolve({
    isSafe,
    remark: ticketData.remark,
    tableDataList,
  });
}
