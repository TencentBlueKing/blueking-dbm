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
interface MongoInstance {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_instance_id?: number;
  instance: string;
  ip: string;
  name?: string;
  phase: string;
  port: number;
  role?: string;
  spec_config: string;
  status: string;
}

export default class MongoDetail {
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_entry_details: {
    cluster_entry_type: string;
    role: string;
    entry: string;
    target_details: {
      app: string,
      bk_cloud_iduid: number,
      dns_str: string,
      domain_name: string,
      domain_typeuid: number,
      ip: string,
      last_change_time: string,
      manager: string,
      port: number,
      remark: string,
      start_time: string,
      status: string,
      uid: number,
    }[];
  }[];
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  instances: {
    bk_cloud_id: number;
    bk_cloud_name: string;
    bk_host_id: number;
    cluster_id: number;
    cluster_name: string;
    cluster_type: string;
    create_at: string;
    host_info?: {
      alive: number,
      biz: {
        id: number,
        name: string
      },
      cloud_area: {
        id: number,
        name: string
      },
      cloud_id: number,
      host_id: number,
      host_name?: string,
      ip: string,
      ipv6: string,
      meta: {
        bk_biz_id: number,
        scope_id: number,
        scope_type: string
      },
      scope_id: string,
      scope_type: string,
      os_name: string,
      bk_cpu?: number,
      bk_disk?: number,
      bk_mem?: number,
      os_type: string,
      agent_id: number,
      cpu: string,
      cloud_vendor: string,
      bk_idc_name?: string,
    };
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
      disaster_tolerance_level: string;
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
    spec_config: string;
    status: string;
  }[];
  major_version: string;
  master_domain: string;
  mongodb: MongoInstance[];
  mongos: MongoInstance[];
  mongo_config: MongoInstance[];
  operations: {
    cluster_id: number,
    flow_id: number,
    status: string,
    ticket_id: number,
    ticket_type: string,
    title: string,
  }[];
  phase: string;
  phase_name: string;
  region: string;
  shard_node_count: number;
  shard_num: number;
  slave_domain: string;
  spec_config: {
    count: number;
    cpu: {
      max: number;
      min: number;
    },
    id: number;
    mem: {
      max: number;
      min: number;
    },
    name: string;
    qps: {
      max: number;
      min: number;
    },
    storage_spec: {
      mount_point: string;
      size: number;
      type: string;
    }[],
  };
  status: string;

  constructor(payload = {} as MongoDetail) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_entry_details = payload.cluster_entry_details;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.instances = payload.instances;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.mongodb = payload.mongodb;
    this.mongos = payload.mongos;
    this.mongo_config = payload.mongo_config;
    this.operations = payload.operations;
    this.phase = payload.phase;
    this.phase_name = payload.phase_name;
    this.region = payload.region;
    this.shard_node_count = payload.shard_node_count;
    this.shard_num = payload.shard_num;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
  }
}
