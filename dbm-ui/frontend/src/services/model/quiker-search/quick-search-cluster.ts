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

import type { ClusterListEntry } from '@services/types';

import { affinityMap, DBTypes, mongodbAffinityMap } from '@common/const';

import { utcDisplayTime } from '@utils';

export default class QuickSearchClusterName {
  bk_biz_id: number;
  bk_cloud_id: number;
  cluster_entry: ClusterListEntry[];
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  creator: string;
  db_module_id: number;
  db_module_name: string;
  db_type: string;
  dba: string;
  disaster_tolerance_level: string;
  id: number;
  is_show_dba: string;
  major_version: string;
  master_domain: string;
  name: string;
  phase: string;
  region: string;
  status: string;
  tags: {
    id: number;
    is_builtin: boolean;
    key: string;
    system: boolean;
    value: string;
  }[];
  time_zone: string;
  update_at: string;
  updater: string;

  constructor(payload = {} as QuickSearchClusterName) {
    this.bk_biz_id = payload.bk_biz_id;
    this.bk_cloud_id = payload.bk_cloud_id;
    this.cluster_entry = payload.cluster_entry || [];
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.db_module_id = payload.db_module_id;
    this.db_module_name = payload.db_module_name;
    this.db_type = payload.db_type;
    this.dba = payload.dba;
    this.disaster_tolerance_level = payload.disaster_tolerance_level;
    this.id = payload.id;
    this.is_show_dba = payload.is_show_dba;
    this.major_version = payload.major_version;
    this.master_domain = payload.master_domain;
    this.name = payload.name;
    this.phase = payload.phase;
    this.region = payload.region;
    this.status = payload.status;
    this.tags = payload.tags || [];
    this.time_zone = payload.time_zone;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get disasterToleranceLevelName() {
    if (this.db_type === DBTypes.MONGODB) {
      return mongodbAffinityMap[this.disaster_tolerance_level as keyof typeof mongodbAffinityMap];
    }
    return affinityMap[this.disaster_tolerance_level as keyof typeof affinityMap];
  }

  get dispalyEntryList() {
    return this.cluster_entry.filter(
      (entryItem) => !(entryItem.cluster_entry_type === 'dns' && entryItem.role === 'master_entry'),
    );
  }

  get displayValue() {
    if (this.cluster_type.includes('k8s')) {
      return (
        this.cluster_entry.find((entryItem) => entryItem.cluster_entry_type === 'clbDns')?.entry || this.cluster_name
      );
    }
    return this.master_domain;
  }
}
