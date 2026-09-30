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

import type OracleHaMachineModel from '@services/model/oracle/oracle-ha-machine';

// 协议主机要素（master / slave 结构）
export interface HostInfo {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
}

// 故障主库主机（Oracle 单机单实例，实例反查结果即主机信息）
export interface FailOverMaster {
  bk_cloud_id: number;
  bk_host_id: number;
  cluster_id: number;
  ip: string;
  // 所属集群域名（反查主机所属集群）
  master_domain: string;
  role: string;
}

// 选择器返回的主机模型
export type SelectorMachine = OracleHaMachineModel;

// 提交单据 info 结构
export interface TicketInfo {
  cluster_id: number;
  master: HostInfo;
  slave: HostInfo;
}

// 主机字段工厂：统一默认值
export const createFailOverMaster = (host: DeepPartial<FailOverMaster> = {}): FailOverMaster => ({
  bk_cloud_id: 0,
  bk_host_id: 0,
  cluster_id: 0,
  ip: '',
  master_domain: '',
  role: '',
  ...host,
});

// 提取协议主机要素：缺省字段按默认值兜底
export const buildHostInfo = (host: Partial<HostInfo> & Pick<HostInfo, 'ip'>): HostInfo => ({
  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
  bk_cloud_id: host.bk_cloud_id ?? 0,
  bk_host_id: host.bk_host_id ?? 0,
  ip: host.ip,
});
