/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited; a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing; software distributed under the License is distributed
 * on an "AS IS" BASIS; WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND; either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/
export default class RedisClusterSpec {
  capacity: number;
  cluster_capacity: number;
  cluster_shard_num: number;
  cpu: {
    min: number;
    max: number;
  };
  creator: string;
  cluster_qps: number;
  desc: string;
  instance_num: number;
  machine_pair: number;
  mem: {
    min: number;
    max: number;
  };
  qps: {
    min: number;
    max: number;
  };
  spec_cluster_type: string;
  spec_id: number;
  spec_machine_type: string;
  spec_name: string;
  storage_spec: {
    mount_point: string;
    size: number;
    type: string;
  }[];

  constructor(payload = {} as RedisClusterSpec) {
    this.capacity = payload.capacity;
    this.cluster_capacity = payload.cluster_capacity;
    this.cluster_shard_num = payload.cluster_shard_num;
    this.cpu = payload.cpu;
    this.creator = payload.creator;
    this.cluster_qps = payload.cluster_qps;
    this.desc = payload.desc;
    this.instance_num = payload.instance_num;
    this.machine_pair = payload.machine_pair;
    this.mem = payload.mem;
    this.qps = payload.qps;
    this.spec_cluster_type = payload.spec_cluster_type;
    this.spec_id = payload.spec_id;
    this.spec_machine_type = payload.spec_machine_type;
    this.spec_name = payload.spec_name;
    this.storage_spec = payload.storage_spec;
  }
}
