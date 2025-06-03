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

import type { HostInfo, MachineRelatedCluster, MachineRelatedInstance, MachineSpecConfig } from '@services/types';

/**
 * 主机详细信息
 */
export interface MachineInfos {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_os_name: string;
  bk_rack_id: number;
  bk_sub_zone: string;
  bk_svr_device_cls_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: number;
  host_info: HostInfo;
  instance_role: string;
  ip: string;
  machine_type: string;
  related_clusters: MachineRelatedCluster[];
  related_instances: MachineRelatedInstance[];
  spec_config: MachineSpecConfig;
  spec_id: number;
}
