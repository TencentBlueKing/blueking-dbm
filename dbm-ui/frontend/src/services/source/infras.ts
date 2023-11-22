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
import type { HostSpec } from '../types/ticket';

const path = '/apis/infras';

export const fetchDbTypeList = function () {
  return http.get<Array<{
    id: string,
    name: string
  }>>(`${path}/dbtype/list_db_types/`);
};

/**
 * 服务器规格列表
 */
export const getInfrasHostSpecs = () => http.get<HostSpec[]>(`${path}/cities/host_specs/`);
