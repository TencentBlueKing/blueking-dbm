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

import type { SpecInfo } from '../../SpecInfos.vue';

// MongoDB 副本集群
export interface DetailsMongoDBReplicaSet {
  bk_cloud_name: string
  cap_spec: string
  city_code: string
  city_name: string
  cluster_alias: string
  cluster_id: number
  cluster_name: string
  cluster_type: string
  db_app_abbr: string
  db_version: string
  disaster_tolerance_level: string
  ip_source: string
  node_count: number
  node_replica_count: number
  oplog_percent: number
  proxy_port: number
  replica_count: number
  replica_sets: Array<{
    domain: string,
    name: string,
    set_id: string,
  }>,
  resource_spec: {
    mongo_machine_set: SpecInfo
  }
  start_port: number
}

// MongoDB 分片集群
export interface DetailsMongoDBSharedCluster {
  bk_cloud_name: string
  cap_key: string
  cap_spec: string
  city_code: string
  city_name: string
  cluster_alias: string
  cluster_id: number
  cluster_name: string
  cluster_type: string
  db_app_abbr: string
  db_version: string
  disaster_tolerance_level: string
  ip_source: string
  oplog_percent: number
  proxy_port: number
  start_port: number
  resource_spec: {
    mongo_config: SpecInfo,
    mongos: SpecInfo,
    mongodb: SpecInfo,
  },
}

// MongoDB 账号授权
export interface MongoDBAuthorizeRules {
  authorize_data?: {
    auth_db: string
    cluster_ids: number[]
    password: string
    rule_sets: {
      db: string
      privileges: string[]
    }[]
    username: string
  }[]
  authorize_uid: string
  excel_url?: string
}

export type TicketDetailTypes = DetailsMongoDBReplicaSet | DetailsMongoDBSharedCluster | MongoDBAuthorizeRules
