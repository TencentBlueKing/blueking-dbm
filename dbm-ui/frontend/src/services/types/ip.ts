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

export interface IpScope {
  scope_id: number,
  scope_type: string
  bk_cloud_id?: number | string
}

/**
 * 校验手动 IP 信息参数
 */
export interface CheckIpParams {
  mode?: string,
  ip_list: string[],
  ipv6_list?: string[],
  key_list?: string[],
  scope_list: IpScope[]
}

export interface HostMeta {
  bk_biz_id: number,
  scope_id: number,
  scope_type: string
}

/**
 * 获取主机详情参数
 */
export interface FetchHostDetailsParams {
  mode?: string,
  host_list: Array<{ host_id: number, meta: HostMeta }>,
  scope_list: IpScope[]
}

/**
 * 获取主机信息参数
 */
export interface FetchHostInfosParams {
  node_list: Array<{ instance_id: number, object_id: string, meta: HostMeta }>,
  page_size: number,
  start: number
  mode?: string
}

/**
 * 获取主机拓扑参数
 */
export interface FetchHostTopoParams {
  mode?: string,
  all_scope: boolean,
  scope_list: IpScope[]
}

/**
 * 主机详情
 */
export interface HostDetails {
  alive: number,
  biz: { id: number, name: string },
  cloud_area: { id: number, name: string },
  cloud_id: number,
  host_id: number,
  host_name: string,
  ip: string,
  ipv6: string,
  meta: HostMeta,
  scope_id: string,
  scope_type: string,
  os_name: string,
  bk_cpu: number | null,
  bk_disk: number | null,
  bk_mem: number | null,
  os_type: string,
  agent_id: number,
  cpu: string,
  cloud_vendor: string,
  bk_idc_name: string | null,
}

/**
 * 主机提交格式
 */
export interface HostSubmitParams {
  ip: string,
  bk_cloud_id: number,
  bk_host_id: number,
  bk_cpu: number | null,
  bk_mem: number | null,
  bk_disk: number | null
  bk_biz_id: number
}

/**
 * 主机拓扑信息
 */
export interface HostTopoInfo {
  bk_cloud_id: number,
  bk_host_id: number,
  ip: string,
  topo: string[]
}

/**
 * 管控区域基本信息
 */
export interface CloudAreaInfo {
  bk_account_id: number,
  bk_cloud_id: number,
  bk_cloud_name: string,
  bk_cloud_vendor: string,
  bk_creator: string,
  bk_last_editor: string,
  bk_region: string,
  bk_status: string,
  bk_status_detail: string,
  bk_supplier_account: string,
  bk_vpc_id: string,
  bk_vpc_name: string,
  create_time: string,
  last_time: string,
}
