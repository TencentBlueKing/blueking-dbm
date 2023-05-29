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

import { utcDisplayTime } from '@utils';

export default class QuickSearchClusterName {
  alias: string;
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  disaster_tolerance_level: string;
  id: number;
  immute_domain: string;
  major_version: string;
  name: string;
  phase: string;
  region: string;
  status: string;
  time_zone: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as QuickSearchClusterName) {
    this.alias = payload.alias;
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.create_at = payload.create_at;
    this.cluster_type = payload.cluster_type;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
    this.id = payload.id;
    this.immute_domain = payload.immute_domain;
    this.major_version = payload.major_version;
    this.name = payload.name;
    this.phase = payload.phase;
    this.region = payload.region;
    this.status = payload.status;
    this.time_zone = payload.time_zone;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }
}
