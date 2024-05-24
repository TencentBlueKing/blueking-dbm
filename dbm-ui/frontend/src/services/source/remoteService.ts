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
import http from '../http';

const getRootPath = () => `/apis/mysql/bizs/${window.PROJECT_CONFIG.BIZ_ID}/remote_service`;

/**
 * 校验DB是否在集群内
 */
export function checkClusterDatabase(params: {
  infos: Array<{
    cluster_id: number;
    db_names: string[];
  }>;
}) {
  return http.post<
    {
      cluster_id: number;
      db_names: string[];
      check_info: Record<string, boolean>;
    }[]
  >(`${getRootPath()}/check_cluster_database/`, params);
}

/**
 * 校验flashback信息是否合法
 */
export function checkFlashbackDatabase(params: {
  infos: Array<{
    cluster_id: number;
    databases: string[];
    databases_ignore: string[];
    tables: string[];
    tables_ignore: string[];
  }>;
}) {
  return http.post<
    {
      cluster_id: number;
      databases: string[];
      databases_ignore: string[];
      message: string;
      tables: string[];
      tables_ignore: string[];
    }[]
  >(`${getRootPath()}/check_flashback_database/`, params);
}

/**
 * 查询集群数据库列表
 */
export function getClusterDatabaseNameList(params: { cluster_ids: Array<number> }) {
  return http.post<
    Array<{
      cluster_id: number;
      databases: Array<string>;
      system_databases: Array<string>;
    }>
  >(`${getRootPath()}/show_cluster_databases/`, params);
}

// 查询集群数据表列表
export function getClusterTablesNameList(params: {
  cluster_db_infos: {
    cluster_id: number;
    dbs: string[];
  }[];
}) {
  return http.post<
    {
      cluster_id: number;
      table_data: Record<string, string[]>;
    }[]
  >(`${getRootPath()}/show_cluster_tables/`, params);
}

// 根据库表正则查询集群库信息
export function showDatabasesWithPatterns(params: {
  infos: {
    cluster_id: number;
    dbs: string[];
    ignore_dbs: string[];
  }[];
}) {
  return http.post<
    {
      cluster_id: number;
      databases: string[];
    }[]
  >(`${getRootPath()}/show_databases_with_patterns/`, params);
}
