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

import DirtyMachinesModel from '@services/model/db-resource/dirtyMachines';

import http from '../http';
import type { ListBase } from '../types';

const path = '/apis/db_dirty';

/**
 * 污点池列表
 */
export function getDirtyMachines(params: { limit: number; offset: number }) {
  return http
    .get<ListBase<DirtyMachinesModel[]>>(`${path}/query_dirty_machines/`, params, {
      catchError: true,
    })
    .then((res) => ({
      ...res,
      results: res.results.map(
        (item) =>
          new DirtyMachinesModel(
            Object.assign(item, {
              permission: Object.assign(item.permission, res.permission),
            }),
          ),
      ),
    }));
}

/**
 * 将污点池主机转移至待回收模块
 */
export function transferDirtyMachines(params: { bk_host_ids: number[] }) {
  return http.post(`${path}/transfer_dirty_machines/`, params);
}

/**
 * 删除污点池记录
 */
export function deleteDirtyRecords(params: { bk_host_ids: number[] }) {
  return http.delete(`${path}/delete_dirty_records/`, params);
}
