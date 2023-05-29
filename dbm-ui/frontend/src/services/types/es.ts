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

type node = {
  ip: string,
  port: number,
}
export interface EsDetail {
  cluster_alias: string,
  cluster_name: string,
  cluster_type: string,
  cluster_type_name: string,
  create_at: string,
  creator: string,
  domain: string,
  hot_nodes: Array<node>,
  id: number,
  major_version: string,
  master_nodes: Array<node>,
  phase: string,
  status: string,
  update_at: string,
  updater: string,
}

export interface EsListNode {
  bk_host_id: number,
  bk_cloud_id: number,
  bk_host_name: string,
  cpu_mem: string,
  ip: string,
  machine_type: string,
  node_count: number,
  role: string,
  status: number
}

export interface EsListInstance {
  bk_host_id: number,
  bk_cloud_id: number,
  cluster_id: number,
  create_at: string,
  domain: string,
  id: number,
  instance_address: string,
  instance_name: string,
  role: string,
  status: string,
}


