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

import type { HostInfo } from '@services/types';

/**
 * 实例详细信息（包含主机、集群）
 */
export interface InstanceInfos {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  cluster_domain: string;
  create_at: string;
  db_module_id: number;
  db_module_name: string;
  host_info: HostInfo;
  instance_address: string;
  ip: string;
  master_domain: string;
  port: number;
  related_clusters: {
    alias: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_name: string;
    cluster_type: string;
    creator: string;
    db_module_id: number;
    id: number;
    major_version: string;
    master_domain: string;
    phase: string;
    region: string;
    status: string;
    time_zone: string;
    updater: string;
  }[];
  role: string;
  spec_config: {
    cpu: number;
    id: number;
    mem: number;
    name: string;
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    };
  };
  status: 'running' | 'unavailable';
}
