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

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';

import http from '../http';

const path = `/apis/sqlserver/bizs/${window.PROJECT_CONFIG.BIZ_ID}`;

/**
 * 判断库名是否在集群存在
 */
export function checkSqlserverDbExist(params: { cluster_id: number; db_list: string[] }) {
  return http.post<Record<string, boolean>>(`${path}/cluster/check_sqlserver_db_exist/`, params);
}

/**
 * 通过库表匹配查询db
 */
export function getSqlserverDbs(params: { cluster_id: number; db_list: string[]; ignore_db_list: string[] }) {
  return http.post<string[]>(`${path}/cluster/get_sqlserver_dbs/`, params);
}

/**
 * 获取业务拓扑树
 */
export function geSqlserverResourceTree(params: { cluster_type: string }) {
  return http.get<BizConfTopoTreeModel[]>(`${path}/resource_tree/`, params);
}

// 通过库表匹配批量查询db
export function getBatchSqlserverDbs(params: { cluster_ids: number[]; db_list: string[]; ignore_db_list: string[] }) {
  return http.post<Record<string, string[]>>(`${path}/cluster/multi_get_dbs_for_drs/`, params);
}

// 导入构造DB数据
export function importDbStruct(params: FormData) {
  return http.post<Record<'db_name' | 'target_db_name' | 'rename_db_name', string>[]>(
    `${path}/cluster/import_db_struct/`,
    params,
  );
}

// 根据时间范围查询集群备份记录
export function queryBackupLogs(params: { cluster_id: number; days?: number }) {
  return http.post<
    {
      backup_id: string;
      end_time: string;
      logs: any[];
      role: string;
      start_time: string;
    }[]
  >(`${path}/rollback/query_backup_logs/`, params);
}

// 根据备份记录和库匹配模式查询操作库
export function queryDbsByBackupLog(params: {
  cluster_id: number;
  db_pattern: string[];
  ignore_db: string[];
  backup_logs?: unknown[];
  rollback_time?: string;
}) {
  return http.post<string[]>(`${path}/rollback/query_dbs_by_backup_log/`, params);
}

// 根据回档时间集群最近备份记录
export function queryLatestBackupLog(params: { cluster_id: number; rollback_time: string }) {
  return http.post<{
    backup_id: string;
    end_time: string;
    start_time: string;
    logs: unknown[];
  }>(`${path}/rollback/query_latest_backup_log/`, params);
}
