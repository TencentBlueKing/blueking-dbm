/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 * for the specific language governing permissions and limitations under the License.
 */

// 上游类型卡片值：single 单节点 / master 主库 / slave 从库
export type UpstreamMode = 'single' | 'master' | 'slave';

// 协议主机要素：old_node / old_master 结构
export interface HostInfo {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  ip: string;
  port: number;
}

// 上游实例（实例选择器返回结构）
export interface UpstreamInstance extends HostInfo {
  cluster_id: number;
  instance_address: string;
  master_domain: string;
  role: string;
  // 当前规格（spec_config.id），用于目标规格列默认填充
  spec_config: {
    id?: number;
  };
  version: string;
}

// 上游实例字段工厂：统一默认值，bk_biz_id 默认当前业务
export const createUpstreamInstance = (instance: Partial<UpstreamInstance> = {}): UpstreamInstance => ({
  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
  bk_cloud_id: 0,
  bk_host_id: 0,
  cluster_id: 0,
  instance_address: '',
  ip: '',
  master_domain: '',
  port: 0,
  role: '',
  spec_config: { id: 0 },
  version: '',
  ...instance,
});

// 提取协议主机要素（old_node / old_master）：缺省字段按默认值兜底
export const buildHostInfo = (host: Partial<HostInfo> & Pick<HostInfo, 'ip' | 'port'>): HostInfo => ({
  bk_biz_id: host.bk_biz_id ?? window.PROJECT_CONFIG.BIZ_ID,
  bk_cloud_id: host.bk_cloud_id ?? 0,
  bk_host_id: host.bk_host_id ?? 0,
  ip: host.ip,
  port: host.port,
});
