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

export default class SpiderMachine {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_type: string;
  create_at: string;
  host_info: {
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
    bk_idc_id: string;
    bk_idc_name: string;
    bk_mem: number;
    cloud_area: {
      id: number;
      name: string;
    };
    cloud_id: number;
    cloud_vendor: string;
    host_id: number;
    host_name: string;
    ip: string;
    ipv6: string;
    meta: {
      bk_biz_id: number;
      scope_id: number;
      scope_type: string;
    };
    os_name: string;
    os_type: number;
  };
  instance_role: string;
  ip: string;
  machine_type: string;
  related_clusters: {
    alias: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    // cluster_name: string;
    cluster_type: string;
    cluster_type_name: string;
    creator: string;
    db_module_id: number;
    disaster_tolerance_level: string;
    id: number;
    immute_domain: string;
    major_version: string;
    phase: string;
    region: string;
    status: string;
    time_zone: string;
    updater: string;
  }[];
  related_instances: {
    name: string;
    ip: string;
    port: 25000;
    instance: string;
    status: string;
    phase: string;
    bk_instance_id: 6076;
    bk_host_id: 247;
    bk_cloud_id: 0;
    spec_config: {
      id: number;
      cpu: {
        max: number;
        min: number;
      };
      mem: {
        max: number;
        min: number;
      };
      qps: {
        max: number;
        min: number;
      };
      name: string;
      count: number;
      device_class: string[];
      storage_spec: {
        size: number;
        type: string;
        mount_point: string;
      }[];
    };
    bk_biz_id: 3;
    admin_port: 26000;
  }[];
  spec_config: {
    id: number;
    cpu: {
      max: number;
      min: number;
    };
    mem: {
      max: number;
      min: number;
    };
    qps: {
      max: number;
      min: number;
    };
    name: string;
    count: number;
    device_class: string[];
    storage_spec: {
      size: number;
      type: string;
      mount_point: string;
    }[];
  };
  spec_id: number;

  constructor(payload = {} as SpiderMachine) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.host_info = payload.host_info;
    this.instance_role = payload.instance_role;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.related_clusters = payload.related_clusters;
    this.related_instances = payload.related_instances;
    this.spec_config = payload.spec_config;
    this.spec_id = payload.spec_id;
  }
}
