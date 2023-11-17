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
import type { ListBase } from '../types/common';

const path = '/apis/db_dirty';

/**
 * 污点池列表
 */
export const getDirtyMachines = function (params: {
  limit: number,
  offset: number,
}, config = { globalError: true }) {
  return http.get<ListBase<DirtyMachinesModel[]>>(`${path}/query_dirty_machines/`, params, config).then(res => ({
    ...res,
    results: res.results.map(item => new DirtyMachinesModel(item)),
  }));
};

/**
 * 将污点池主机转移至待回收模块
 */
export const transferDirtyMachines = function (params: {
  bk_host_ids: number[]
}) {
  return http.post(`${path}/transfer_dirty_machines/`, params);
};
