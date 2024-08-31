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

import MigrateRecordModel from '@services/model/sqlserver/migrate-record';

import http from '../http';

const getPath = () => `/apis/sqlserver/bizs/${window.PROJECT_CONFIG.BIZ_ID}/migrate`;

/**
 * 获取迁移记录
 */
export function getList(params: { cluster_name?: string }) {
  return http
    .get<MigrateRecordModel[]>(`${getPath()}/query_migrate_records/`, params)
    .then((data) => data.map((item) => new MigrateRecordModel(item)));
}

// 强制终止
export function forceFailedMigrate(params: { dts_id: number }) {
  return http.post(`${getPath()}/force_failed_migrate/`, params);
}

// 断开同步
export function manualTerminateSync(params: { ticket_id: number }) {
  return http.post<{ ticket_id: number }>(`${getPath()}/manual_terminate_sync/`, params);
}
