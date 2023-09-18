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

export default class KafkaNode {
  static ROLE_BROKER = 'broker';
  static ROLE_ZOOKEEPER = 'zookeeper';

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_host_name: string;
  cpu_mem: string;
  ip: string;
  machine_type: string;
  node_count: number;
  role: string;
  create_at: string;
  status: number;

  constructor(payload = {} as KafkaNode) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_host_name = payload.bk_host_name;
    this.cpu_mem = payload.cpu_mem;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.node_count = payload.node_count;
    this.role = payload.role;
    this.status = payload.status;
    this.create_at = payload.create_at;
  }

  get isBroker() {
    return this.role === KafkaNode.ROLE_BROKER;
  }

  get isZookeeper() {
    return this.role === KafkaNode.ROLE_ZOOKEEPER;
  }
}
