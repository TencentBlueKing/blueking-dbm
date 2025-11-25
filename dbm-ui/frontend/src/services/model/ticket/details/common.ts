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

import type { ClusterTypes } from '@common/const';

export interface DetailBase {
  __ticket_detail__: string;
}

export interface DetailClusters {
  [clusterId: number]: {
    alias: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_cloud_name: string;
    cluster_type: ClusterTypes;
    cluster_type_name: string;
    creator: string;
    db_module_id: number;
    disaster_tolerance_level: string;
    id: number;
    immute_domain: string;
    major_version: string;
    name: string;
    phase: string;
    region: string;
    status: string;
    tag: any[];
    time_zone: string;
    updater: string;
  };
}

export interface DetailInstances {
  [instanceId: number]: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    bk_sub_zone: string;
    instance: string;
    ip: string;
    is_stand_by: true;
    name: string;
    phase: string;
    port: number;
    spec_config: DetailSpecs;
    status: string;
    version: string;
  };
}

export interface DetailSpecs {
  [key: string]: {
    capacity: number;
    count: number;
    cpu: {
      max: number;
      min: number;
    };
    device_class: string[];
    id: number;
    mem: {
      max: number;
      min: number;
    };
    name: string;
    qps: {
      max: number;
      min: number;
    };
    spec_id: number;
    storage_spec: {
      max: number;
      min: number;
      mount_point: string;
      size?: number;
      type: string;
    }[];
  };
}

export interface DetailMachines {
  [key: string]: {
    instance_role: string;
    related_clusters: number[];
    related_instances: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      bk_instance_id: number;
      bk_sub_zone: string;
      instance: string;
      ip: string;
      is_stand_by: boolean;
      name: string;
      phase: string;
      port: number;
      spec_config: {
        id: number;
      };
      status: string;
      version: string;
    }[];
    spec_config: DetailSpecs[string];
  };
}

export interface ApplySpecInfo {
  affinity: string;
  count: number;
  cpu: {
    max: number;
    min: number;
  };
  label_names: string[]; // 标签名称列表，单据详情回显用
  labels: string[]; // 标签id列表
  location_spec: {
    city: string;
    include_or_exclue?: boolean;
    sub_zone_ids?: number[];
  };
  mem: {
    max: number;
    min: number;
  };
  qps: {
    max: number;
    min: number;
  };
  spec_id: number;
  spec_name: string;
  storage_spec: {
    max: number;
    min: number;
    mount_point: string;
    size?: number;
    type: string;
  }[];
}

export interface NodeInfo {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_cpu: number;
  bk_disk: number;
  bk_host_id: number;
  bk_mem: number;
  city: string;
  device_class: string;
  ip: string;
  rack_id: string;
  storage_device: Record<string, any>;
  sub_zone: string;
  sub_zone_id: string;
}
