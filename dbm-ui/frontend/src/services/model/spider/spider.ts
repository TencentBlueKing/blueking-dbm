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
import { PipelineStatus } from '@common/const';

export default class Spider {
  bk_biz_id: number;
  bk_biz_name: string;
  bk_cloud_id: number;
  bk_cloud_name: string;
  cluster_capacity: number;
  cluster_name: string;
  cluster_shard_num: number;
  cluster_spec: {
    cpu: {
      max: number;
      min: number;
    };
    creator: string;
    desc: string;
    device_class: Record<string, any>[];
    mem: {
      max: number;
      min: number;
    };
    instance_num: number;
    qps: {
      max: number;
      min: number;
    };
    spec_cluster_type: string;
    spec_id: number;
    spec_machine_type: string;
    spec_name: string;
    storage_spec: {
      size: number;
      type: string;
      mount_point: string;
    }[];
  };
  cluster_type: string;
  cluster_entry_details: {
    cluster_entry_type: string;
    entry: string;
    role: string;
    target_details: {
      app: string;
      bk_cloud_iduid: number;
      dns_str: string;
      domain_name: string;
      domain_typeuid: number;
      ip: string;
      last_change_time: string;
      manager: string;
      port: number;
      remark: string;
      start_time: string;
      status: string;
      uid: number;
    }[];
  }[];
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  id: number;
  machine_pair_cnt: number;
  major_version: string;
  master_domain: string;
  operations: Array<{
    cluster_id: number;
    flow_id: number;
    status: PipelineStatus;
    ticket_id: number;
    ticket_type: string;
    title: string;
  }>;
  phase: string;
  region: string;
  remote_db: {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_instance_id: number;
    instance: string;
    ip: string;
    name: string;
    phase: string;
    port: number;
    status: string;
    spec_config: {
      count: number;
      cpu: {
        max: number;
        min: number;
      };
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
      storage_spec: {
        mount_point: string;
        size: number;
        type: string;
      }[];
    };
  }[];
  remote_dr: Spider['remote_db'];
  remote_shard_num: number;
  slave_domain: string;
  spider_master: Spider['remote_db'];
  spider_mnt: Spider['remote_db'];
  spider_slave: Spider['remote_db'];
  status: string;

  constructor(payload = {} as Spider) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_biz_name = payload.bk_biz_name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.cluster_capacity = payload.cluster_capacity;
    this.cluster_name = payload.cluster_name;
    this.cluster_shard_num = payload.cluster_shard_num;
    this.cluster_spec = payload.cluster_spec;
    this.cluster_type = payload.cluster_type;
    this.cluster_entry_details = payload.cluster_entry_details;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.id = payload.id;
    this.machine_pair_cnt = payload.machine_pair_cnt;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.operations = payload.operations || [];
    this.phase = payload.phase;
    this.region = payload.region;
    this.remote_db = payload.remote_db || [];
    this.remote_dr = payload.remote_dr || [];
    this.remote_shard_num = payload.remote_shard_num;
    this.slave_domain = payload.slave_domain;
    this.spider_master = payload.spider_master || [];
    this.spider_mnt = payload.spider_mnt || [];
    this.spider_slave = payload.spider_slave || [];
    this.status = payload.status;
  }

  get isClusterNormal() {
    return this.status === 'normal';
  }
}
