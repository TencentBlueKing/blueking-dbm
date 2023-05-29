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

export interface HdfsDetail {
  cluster_alias: string,
  cluster_name: string,
  cluster_type: string,
  cluster_type_name: string,
  create_at: string,
  creator: string,
  domain: string,
  id: number,
  major_version: string,
  phase: string,
  status: string,
  update_at: string,
  updater: string,
  bk_cloud_id: number,
  bk_cloud_name: string,
}

export interface HdfsListNode {
  bk_host_id: number,
  bk_cloud_id: number,
  cpu_mem: string,
  ip: string,
  machine_type: string,
  node_count: number,
  role: string,
  role_set: Array<string>,
  status: number
}

export interface HdfsListInstance {
  bk_host_id: number,
  bk_cloud_id: number,
  cluster_id: number,
  created_at: string,
  domain: string,
  id: number,
  instance_address: string,
  instance_name: string,
  role: string,
  status: string,
}
