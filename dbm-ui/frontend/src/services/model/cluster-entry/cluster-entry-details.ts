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

export interface DnsTargetDetails {
  app: string;
  bk_cloud_id: number;
  dns_str: string;
  domain_name: string;
  domain_type: number;
  ip: string;
  last_change_time: string;
  manager: string;
  port: number;
  remark: string;
  start_time: string;
  status: string;
  uid: number;
}

export interface ClbPolarisTargetDetails {
  alias_token: string;
  creator: string;
  clb_ip: string;
  clb_id: string;
  clb_domain: string;
  entry: number;
  id: number;
  polaris_l5: string;
  polaris_name: string;
  polaris_token: string;
  port: number;
  updater: string;
  url: string;
}

export default class ClusterEntryDetail<T extends unknown | DnsTargetDetails | ClbPolarisTargetDetails = unknown> {
  cluster_entry_type: string; // 'dns' | 'clb' | 'polaris' | 'clbDns'
  entry: string;
  role: string;
  target_details: T[];

  constructor(payload = {} as ClusterEntryDetail<T>) {
    this.cluster_entry_type = payload.cluster_entry_type;
    this.entry = payload.entry;
    this.role = payload.role;
    this.target_details = payload.target_details;
  }

  get isDns() {
    return this.cluster_entry_type === 'dns';
  }

  get isClb() {
    return this.cluster_entry_type === 'clb';
  }

  get isPolaris() {
    return this.cluster_entry_type === 'polaris';
  }

  get isNodeEntry() {
    return this.role === 'node_entry';
  }
}
