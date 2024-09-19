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

const path = '/apis/conf/system_settings';

/**
 * 查询环境变量
 */
export function getSystemEnviron() {
  return http.get<{
    AFFINITY: {
      label: string;
      value: string;
    }[];
    BK_CMDB_URL: string;
    BK_COMPONENT_API_URL: string;
    BK_DBM_URL: string;
    BK_DOMAIN: string;
    BK_HELPER_URL: string;
    BK_NODEMAN_URL: string;
    BK_SCR_URL: string;
    CC_IDLE_MODULE_ID: string;
    CC_MANAGE_TOPO: {
      dirty_module_id: number;
      resource_module_id: number;
      set_id: number;
    };
    DBA_APP_BK_BIZ_ID: number;
    DBA_APP_BK_BIZ_NAME: number;
    ENABLE_EXTERNAL_PROXY: boolean;
  }>(`${path}/environ/`);
}

// 查询机型类型
export const getDeviceClassList = function () {
  return http.get<string[]>(`${path}/device_classes/`);
};
