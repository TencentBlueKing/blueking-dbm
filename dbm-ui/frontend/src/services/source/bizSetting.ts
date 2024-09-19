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

const path = '/apis/conf/biz_settings';

/**
 * 创建业务配置
 */
export const create = function (params: { bk_biz_id: number; type: string; key: string; value: any }) {
  return http.post(`${path}/`, params);
};
/**
 * 更新业务配置
 */
export const update = function (params: { id: number }) {
  return http.post(`${path}/`, params);
};

// 业务设置列表键值映射表
export const getBizSettingList = function (params: { bk_biz_id: number; key?: string }) {
  return http.get<Record<string, any>>(`${path}/simple/`, params);
};

// 更新业务设置列表键值
export const updateBizSetting = function (params: { bk_biz_id: number; key: string; value: any; value_type?: string }) {
  return http.post(`${path}/update_settings/`, params);
};
