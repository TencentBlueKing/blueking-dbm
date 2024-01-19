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
    create_time: '2024-01-18',
    create_user: 'UserA',
    instance_name: 'Instance1',
    master_enter: 'Enter1',
    operation: 'Operate1',
    slave_enter: 'Enter2',
    status: 'running',
    isNew: false,
    bk_host_id: 101,
    dbStatusConfigureObj: {
      text: '',
      theme: '',
    },
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
      {
        ip: '002',
        name: '192.167:1200',
        port: 12000,
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
    create_time: '2024-01-19',
    create_user: 'UserB',
    instance_name: 'Instance2',
    master_enter: 'Enter3',
    operation: 'Operate2',
    slave_enter: 'Enter4',
    status: 'running',
    isNew: true,
    bk_host_id: 102,
    dbStatusConfigureObj: {
      text: 'DB status text 1',
      theme: 'DB theme 1',
    },
    clusterId: 73,
    bk_cloud_name: 'Cloudserver',
    cluster_type: '集群类型A',
    proxies: [
      {
        ip: '003',
        name: '192.168.1.3:6000',
        port: 6000,
        status: '3000',
        bk_instance_id: 1000,
      },
      {
        ip: '004',
        name: '192.168.1.4:7000',
        port: 7000,
        status: '3000',
        bk_instance_id: 1001,
      },
    ],
  },
  {
    id: 3,
    belong_DB_module: 'Module3',
    cluster_name: 'ClusterC',
    control_area: 'Area53',
    create_time: '2024-01-20',
    create_user: 'UserC',
    instance_name: 'Instance3',
    master_enter: 'Enter5',
    operation: 'Operate3',
    slave_enter: 'Enter6',
    status: 'maintenance',
    isNew: false,
    bk_host_id: 103,
    dbStatusConfigureObj: {
      text: 'DB status text 2',
      theme: 'DB theme 2',
    },
    clusterId: 74,
    bk_cloud_name: 'Datacenter',
    cluster_type: '集群类型B',
    proxies: [
      {
        ip: '005',
        name: '192.168.1.5:8000',
        port: 8000,
        status: '4000',
        bk_instance_id: 1002,
      },
      {
        ip: '006',
        name: '192.168.1.6:9000',
        port: 9000,
        status: '4000',
        bk_instance_id: 1003,
      },
    ],
  },
];

const detailData = {
  bk_biz_id: 3,
  bk_biz_name: 'DBA',
  bk_cloud_id: 0,
  bk_cloud_name: '直连区域',
  cluster_entry_details: [{
    cluster_entry_type: 'dns',
    role: 'master_entry',
    entry: 'feichaidb.durant1213-1.dba.db',
    target_details: [{
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
    }],
  }],
  cluster_name: 'durant1213-1',
  cluster_type: 'tendbsingle',
  clusterId: 99,
  create_at: '2023-12-13T21:56:10+08:00',
  creator: 'admin',
  db_module_name: 'feichai',
  id: 99,
  master_domain: 'feichaidb.durant1213-1.dba.db',
  masters: [{
    bk_biz_id: 3,
    bk_cloud_id: 0,
    bk_host_id: 182,
    bk_instance_id: 6272,
    ip: '9.146.107.245',
    name: '',
    phase: 'online',
    port: 20000,
    spec_config: {
      id: 0,
    },
    status: 'running',
  }],
  operations: [{
    cluster_id: 99,
    flow_id: 4695,
    operator: 'durant',
    status: 'RUNNING',
    ticket_id: 1902,
    ticket_type: 'SQLSERVER_HA_DISABLE',
    title: 'SqlServer主从节点禁用',
  }],
  phase: 'online',
  status: 'normal',
};

/**
 * 获取集群列表数据
 */
export function gethaClusterList() {
  return Promise.resolve(listData.map(item => new SqlServerClusterListModel(item)));
}

/**
 * 获取列表数据
 */
export function gethaClusterDetail() {
  return Promise.resolve(new SqlserverClusterDetailModel(detailData));
}

/**
 * 导出实例数据为 excel 文件
 */
export function exportSqlserverHaClusterToExcel(params: { bk_host_ids?: number[] }) {
  return http.post<string>(`${path}/export_instance/`, params, { responseType: 'blob' });
}
