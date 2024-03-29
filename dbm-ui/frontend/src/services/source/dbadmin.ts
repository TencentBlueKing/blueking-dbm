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

const path = '/apis/conf/db_admin';

interface UpdateAdminsParams {
  bk_biz_id: number;
  db_admins: {
    db_type: string;
    users: string[];
    db_type_display: string;
  }[];
}

/**
 * 查询 DBA 人员列表
 */
export function getAdmins(params: { bk_biz_id: number }) {
  return http.get<UpdateAdminsParams['db_admins']>(`${path}/list_admins/`, params);
}

/**
 * 更新 DBA 人员列表
 */
export function updateAdmins(params: UpdateAdminsParams) {
  return http.post<UpdateAdminsParams>(`${path}/upsert_admins/`, params);
}
