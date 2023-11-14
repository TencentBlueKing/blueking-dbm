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

const path = '/apis/conf/profile';

/**
 * 个人配置信息
 */
export interface ProfileItem {
  label: string,
  values: any
}

/**
 * 个人配置列表
 */
export const getProfile = function () {
  return http.get<{
    profile: ProfileItem[],
    username: string,
    is_manager: boolean
  }>(`${path}/get_profile/`);
};

/**
 * 更新个人配置列表
 */
export const upsertProfile = function (params: ProfileItem) {
  return http.post(`${path}/upsert_profile/`, params);
};
