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

export default class HdfsNode {
  static ROLE_DATA_NODE = 'hdfs_datanode';
  static ROLE_JOURNAL_NODE = 'hdfs_journalnode';
  static ROLE_ZOOKEEPER = 'hdfs_zookeeper';
  static ROLE_NAME_NODE = 'hdfs_namenode';

  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  bk_host_name: string;
  cpu: number;
  create_at: string;
  disk: number;
  ip: string;
  machine_type: string;
  mem: number;
  node_count: number;
  role_set: Array<string>;
  status: number;

  constructor(payload = {} as HdfsNode) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.bk_host_name = payload.bk_host_name;
    this.cpu = payload.cpu || 0;
    this.create_at = payload.create_at;
    this.disk = payload.disk || 0;
    this.ip = payload.ip;
    this.machine_type = payload.machine_type;
    this.mem = payload.mem;
    this.node_count = payload.node_count || 0;
    this.role_set = payload.role_set;
    this.status = payload.status || 0;
  }

  get isDataNode() {
    return this.role_set.includes(HdfsNode.ROLE_DATA_NODE);
  }

  get isJournalNode() {
    return this.role_set.includes(HdfsNode.ROLE_JOURNAL_NODE);
  }
  get isZookeeper() {
    return this.role_set.includes(HdfsNode.ROLE_ZOOKEEPER);
  }
  get isNameNode() {
    return this.role_set.includes(HdfsNode.ROLE_NAME_NODE);
  }
}
