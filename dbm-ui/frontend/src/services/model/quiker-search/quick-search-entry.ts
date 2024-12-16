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

export default class QuickSearchEntry {
  bk_biz_id: number;
  cluster_entry_type: string;
  cluster_id: number;
  cluster_status: string;
  cluster_type: string;
  db_module_name: string;
  db_type: string;
  dba: string;
  disaster_tolerance_level: string;
  entry: string;
  id: number;
  immute_domain: string;
  is_show_dba: string;
  region: string;
  role: string;

  constructor(payload = {} as QuickSearchEntry) {
    this.bk_biz_id = payload.bk_biz_id;
    this.cluster_entry_type = payload.cluster_entry_type;
    this.cluster_id = payload.cluster_id;
    this.cluster_status = payload.cluster_status;
    this.cluster_type = payload.cluster_type;
    this.db_module_name = payload.db_module_name;
    this.db_type = payload.db_type;
    this.dba = payload.dba;
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
    this.entry = payload.entry;
    this.id = payload.id;
    this.immute_domain = payload.immute_domain;
    this.is_show_dba = payload.is_show_dba;
    this.region = payload.region;
    this.role = payload.role;
  }
}
