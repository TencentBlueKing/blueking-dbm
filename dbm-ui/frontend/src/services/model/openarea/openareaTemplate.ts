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
import { utcDisplayTime } from '@utils';

export default class Opeanarea {
  bk_biz_id: number;
  config_name: string;
  config_rules: {
    data_tblist: string[];
    priv_data: number[];
    schema_tblist: string[];
    source_db: string;
    target_db_pattern: string;
  }[];
  create_at: string;
  creator: string;
  id: number;
  permission: {
    mysql_openarea_config_destroy: boolean;
    mysql_openarea_config_update: boolean;
    tendb_openarea_config_destroy: boolean;
    tendb_openarea_config_update: boolean;
  };
  source_cluster: {
    bk_cloud_id: number;
    cluster_type: string;
    id: number;
    immute_domain: string;
    major_version: string;
    name: string;
    region: string;
  };
  source_cluster_id: number;
  update_at: string;
  updater: string;

  constructor(payload = {} as Opeanarea) {
    this.bk_biz_id = payload.bk_biz_id;
    this.config_name = payload.config_name;
    this.config_rules = payload.config_rules || [];
    this.create_at = payload.create_at;
    this.creator = payload.creator;
    this.id = payload.id;
    this.permission = payload.permission || {};
    this.source_cluster = payload.source_cluster || {};
    this.source_cluster_id = payload.source_cluster_id;
    this.update_at = payload.update_at;
    this.updater = payload.updater;
  }

  get updateAtDisplay() {
    return utcDisplayTime(this.update_at);
  }
}
