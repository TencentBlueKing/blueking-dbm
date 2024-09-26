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

/**
 * 主机详情
 */
export interface HostInfo {
  agent_id: number;
  alive: number;
  biz: {
    id: number;
    name: string;
  };
  bk_cpu: number;
  bk_cpu_architecture: string;
  bk_cpu_module: string;
  bk_disk: number;
  bk_host_outerip: string;
  bk_idc_id: number;
  bk_idc_name: string;
  bk_mem: number;
  cloud_area: { id: number; name: string };
  cloud_id: number;
  cloud_vendor: string;
  host_id: number;
  host_name: string;
  ip: string;
  ipv6: string;
  meta: {
    bk_biz_id: number;
    scope_id: string;
    scope_type: string;
  };
  occupancy: boolean;
  os_name: string;
  os_type: string;
}
