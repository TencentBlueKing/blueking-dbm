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

import { useGlobalBizs } from '@stores';

import http from '../http';
import SqlserverClusterDetailModel from '../model/sqlserver/sqlserver-cluster-detail';
import SqlServerClusterListModel from '../model/sqlserver/sqlserver-cluster-list';

const { currentBizId } = useGlobalBizs();

const path = `/apis/sqlserver/bizs/${currentBizId}/sqlserver_resources`;

const listData: SqlServerClusterListModel[] = [
  {
    id: 1,
    belong_DB_module: 'Module1',
    cluster_name: 'ClusterA',
    control_area: 'Area51',
    create_time: '2024-01-12',
    create_user: 'UserA',
    instance_name: 'Instance1',
    master_enter: 'Enter1',
    operation: 'Operate1',
    slave_enter: 'Enter2',
    status: 'unavailable',
    isNew: false,
    bk_host_id: 101,
    dbStatusConfigureObj: { text: '', theme: '' },
    clusterId: 72,
    bk_cloud_name: 'Gamesver',
    cluster_type: '集群类型',
    proxies: [
      {
        ip: '001',
        name: '192.168.1.2:5000',
        port: 5000,
        status: '2000',
        bk_instance_id: 999,
      },
    ],
  },
  {
    id: 2,
    belong_DB_module: 'Module2',
    cluster_name: 'ClusterB',
    control_area: 'Area52',
    create_time: '2024-01-09 11:00:00',
    create_user: 'UserB',
    instance_name: 'Instance2',
    master_enter: 'Enter3', status: 'running',
    isNew: false,
    operation: 'Operate2', dbStatusConfigureObj: { text: '', theme: '' },
    slave_enter: 'Enter4',
    bk_host_id: 102,
    clusterId: 12,
    bk_cloud_name: 'Gamesver',
    cluster_type: '集群类型',
    proxies: [{
      ip: '001', name: '192.168.1.2:5000', port: 5000, status: '2000', bk_instance_id: 999,
    }],
  },
  {
    id: 3,
    belong_DB_module: 'Module3',
    cluster_name: 'ClusterC', status: 'running',
    dbStatusConfigureObj: { text: '', theme: '' },
    control_area: 'Area53',
    create_time: '2023-03-03 12:00:00',
    create_user: 'UserC',
    instance_name: 'Instance3',
    master_enter: 'Enter5',
    operation: 'Operate3',
    slave_enter: 'Enter6',
    isNew: false,
    bk_host_id: 103,
    clusterId: 1003,
    bk_cloud_name: 'Gamesver',
    cluster_type: '集群类型',
    proxies: [{
      ip: '001', name: '192.168.1.2:5000', port: 5000, status: '2000', bk_instance_id: 999,
    }],
  },
];

const detailData = {
  id: 99,
  phase: 'online',
  status: 'normal',
  operations: [
    {
      operator: 'durant',
      cluster_id: 99,
      flow_id: 4695,
      ticket_id: 1902,
      ticket_type: 'SQLSERVER_SINGLE_DISABLE',
      title: 'SQLSERVER 单节点禁用',
      status: 'RUNNING',
    },
  ],
  cluster_name: 'durant1213-1',
  cluster_type: 'tendbsingle',
  bk_biz_id: 3,
  bk_biz_name: 'DBA',
  bk_cloud_id: 0,
  bk_cloud_name: '直连区域',
  master_domain: 'feichaidb.durant1213-1.dba.db',
  masters: [
    {
      name: '',
      ip: '9.146.107.245',
      port: 20000,
      instance: '9.146.107.245:20000',
      status: 'running',
      phase: 'online',
      bk_instance_id: 6272,
      bk_host_id: 182,
      bk_cloud_id: 0,
      spec_config: {
        id: 0,
      },
      bk_biz_id: 3,
    },
  ],
  db_module_name: 'feichai',
  creator: 'admin',
  create_at: '2023-12-13T21:56:10+08:00',
  cluster_entry_details: [
    {
      cluster_entry_type: 'dns',
      role: 'master_entry',
      entry: 'feichaidb.durant1213-1.dba.db',
      target_details: [
        {
          app: '3',
          bk_cloud_id: 0,
          dns_str: '',
          domain_name: 'feichaidb.durant1213-1.dba.db.',
          domain_type: 0,
          ip: '9.146.107.245',
          last_change_time: '2023-12-16T02:49:51+08:00',
          manager: 'DBAManager',
          port: 20000,
          remark: '',
          start_time: '2023-12-16T02:49:51+08:00',
          status: '1',
          uid: 927,
        },
      ],
    },
  ],
};

/**
 * 获取集群列表数据
 */
export function getSingleClusterList() {
  return Promise.resolve(listData.map(item => new SqlServerClusterListModel(item)));
}

/**
 * 获取列表数据
 */
export function getSingleClusterDetail() {
  return Promise.resolve(new SqlserverClusterDetailModel(detailData));
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportSqlserverSingleClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}
