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

export default class QuickSearchInstance {
  bk_biz_id: number;
  bk_cloud_id: number;
  bk_host_id: number;
  bk_idc_area: string;
  bk_idc_name: string;
  cluster_alias: string;
  cluster_domain: string;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  id: number;
  ip: string;
  machine_id: number;
  machine_type: string;
  major_version: string;
  name: string;
  phase: string;
  port: number;
  role: string;
  status: string;

  constructor(payload = {} as QuickSearchInstance) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_host_id = payload.bk_host_id;
    this.bk_idc_area = payload.bk_idc_area;
    this.bk_idc_name = payload.bk_idc_name;
    this.cluster_alias = payload.cluster_alias;
    this.cluster_domain = payload.cluster_domain;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.id = payload.id;
    this.ip = payload.ip;
    this.machine_id = payload.machine_id;
    this.machine_type = payload.machine_type;
    this.major_version = payload.major_version;
    this.name = payload.name;
    this.phase = payload.phase;
    this.port = payload.port;
    this.role = payload.role;
    this.status = payload.status;
  }

  get instance() {
    return `${this.ip}:${this.port}`;
  }
}
