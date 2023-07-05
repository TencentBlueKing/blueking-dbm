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

export default class Redis {
  alias: string;
  bk_biz_id: number;
  bk_cloud_id: number;
  creator: string;
  create_at: string;
  count: number;
  cloud_info: {
    bk_cloud_id: number,
    bk_cloud_name: string
  };
  cluster_type: string;
  db_module_id: number;
  deploy_plan_id: number;
  id: number;
  immute_domain: string;
  major_version: string;
  name: string;
  phase: string;
  proxy_count: number;
  region: string;
  status: string;
  storage_count: number;
  time_zone: string;
  updater: string;
  update_at: string;

  constructor(payload = {} as Redis) {
    this.bk_biz_id = payload.bk_biz_id;
    this.name = payload.name;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.alias = payload.alias;
    this.db_module_id = payload.db_module_id;
    this.immute_domain = payload.immute_domain;
    this.cluster_type = payload.cluster_type;
    this.time_zone = payload.time_zone;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.major_version = payload.major_version;
    this.deploy_plan_id = payload.deploy_plan_id;
    this.phase = payload.phase;
    this.region = payload.region;
    this.status = payload.status;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
    this.proxy_count = payload.proxy_count;
    this.storage_count = payload.storage_count;
    this.cloud_info = payload.cloud_info;
    this.count = this.proxy_count + this.storage_count;
  }
}
