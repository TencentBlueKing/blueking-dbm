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

import DBAdminModel from '@services/model/db-admin/db-admin';
import DBAdminOperationRecordModel from '@services/model/db-admin/db-admin-operation_record';
import type { ListBase } from '@services/types';

import { DBAOperateTypes, DBARoleTypes, type DBTypes } from '@common/const';

import http from '../http';

const path = '/apis/conf/db_admin';

interface Operate {
  after: string;
  before: string;
  bk_biz_id: number;
  db_type?: DBTypes;
  role?: DBARoleTypes;
  type: DBAOperateTypes;
}

/**
 * 查询 DBA 人员列表
 */
export function getAdmins(params: {
  // 参数二选一
  bk_biz_id?: number;
  db_type?: DBTypes;
}) {
  return http
    .get<{
      data: DBAdminModel[];
      permission: DBAdminModel['permission'];
    }>(`${path}/list_admins/`, params)
    .then((data) => ({
      ...data,
      data: data.data.map(
        (item) =>
          new DBAdminModel(
            Object.assign(item, {
              permission: Object.assign({}, item.permission, data.permission),
            }),
          ),
      ),
    }));
}

/**
 * 更新 DBA 人员列表
 */
export function updateAdmins(params: {
  bk_biz_id: number;
  db_admins: {
    db_type: string;
    db_type_display: string;
    users: string[];
  }[];
  operates: Operate[];
}) {
  return http.post(`${path}/upsert_admins/`, params);
}

/**
 * 全局更新 DBA 人员列表
 */
export function updateGlobalAdmins(params: {
  bk_biz_id: number;
  db_admins: {
    db_type: string;
    db_type_display: string;
    users: string[];
  }[];
  operates: Operate[];
}) {
  return http.post(`${path}/upsert_global_admins/`, params);
}

/**
 * 精确查询：判断当前用户是否为指定业务+组件的 DBA
 */
export function checkBizDba(params: { bk_biz_id: number; db_type: string }) {
  return http.post<{ is_biz_dba: boolean }>(`${path}/get_dba_component/`, params);
}

/**
 * 组件列表查询：获取当前用户关联的所有组件类型（跨业务去重）
 */
export function getUserDbaComponents() {
  return http.post<{
    component: {
      db_type: string;
      db_type_display: string;
    }[];
  }>(`${path}/get_dba_component/`);
}

/**
 * 业务纳管
 */
export function manageBiz(params: {
  app_code?: string;
  bk_biz_id: number;
  db_admins: { db_type: DBTypes; users: string[] }[];
}) {
  return http.post(`${path}/manage_biz/`, params);
}

/**
 *  取消纳管
 */
export function cancelManageBiz(params: { bk_biz_id: number }) {
  return http.post(`${path}/cancel_manage_biz/`, params);
}

/**
 * 更新业务标签
 */
export function updateAppTag(params: { bk_biz_id: number; operate: Operate; tags: number[] }) {
  return http.post(`${path}/update_app_tag/`, params);
}

/**
 * 批量更新 DBA
 */
export function batchUpsertAdmins(params: {
  operates: Operate[];
  update_info: {
    bk_biz_id: number;
    db_admins: { db_type: DBTypes; users: string[] }[];
  }[];
}) {
  return http.post(`${path}/batch_upsert_admins/`, params);
}

/**
 * 操作记录
 */
export function getAppOprationRecord(params: { bk_biz_id?: number; limit?: number; offset?: number }) {
  return http.get<ListBase<DBAdminOperationRecordModel[]>>(`${path}/app_operate_log/`, params).then((data) => ({
    ...data,
    results: data.results.map((item) => new DBAdminOperationRecordModel(item)),
  }));
}
