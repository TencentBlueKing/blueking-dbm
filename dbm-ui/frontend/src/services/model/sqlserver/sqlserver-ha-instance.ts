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

import {
  clusterInstStatus,
  ClusterInstStatusKeys,
} from '@common/const';

import {
  isRecentDays,
  utcDisplayTime,
} from '@utils';

import type { HostDetails } from '../../types';

export default class SqlServerHaInstance {
  bk_cloud_id: number;
  bk_cloud_name: string;
  bk_host_id: number;
  cluster_id: number;
  cluster_name: string;
  cluster_type: string;
  create_at: string;
  db_module_id: number;
  host_info: HostDetails;
  id: number;
  instance_address: string;
  ip: string;
  master_domain: string;
  port: number;
  related_clusters?: {
    alias: string;
    bk_biz_id: number;
    bk_cloud_id: number;
    cluster_name: string;
    cluster_type: string;
    creator: string;
    db_module_id: number;
    id: number;
    major_version: string;
    master_domain: string;
    phase: string;
    region: string;
    status: string;
    time_zone: string
    updater: string;
  }[];
  role: string;
  slave_domain: string;
  spec_config: {
    id: number
  };
  status: ClusterInstStatusKeys;
  version: string;

  constructor(payload: SqlServerHaInstance) {
    this.bk_cloud_id = payload.bk_cloud_id;
    this.bk_cloud_name = payload.bk_cloud_name;
    this.bk_host_id = payload.bk_host_id;
    this.cluster_id = payload.cluster_id;
    this.cluster_name = payload.cluster_name;
    this.cluster_type = payload.cluster_type;
    this.create_at = payload.create_at;
    this.db_module_id = payload.db_module_id;
    this.host_info = payload.host_info;
    this.id = payload.id;
    this.instance_address = payload.instance_address;
    this.ip = payload.ip;
    this.master_domain = payload.master_domain;
    this.port = payload.port;
    this.related_clusters = payload.related_clusters;
    this.role = payload.role;
    this.slave_domain = payload.slave_domain;
    this.spec_config = payload.spec_config;
    this.status = payload.status;
    this.version = payload.version;
  }

  get isNew() {
    return isRecentDays(this.create_at, 24 * 3);
  }

  get createAtDisplay() {
    return utcDisplayTime(this.create_at);
  }

  get statusInfo() {
    return clusterInstStatus[this.status] || clusterInstStatus.unavailable;
  }
}
