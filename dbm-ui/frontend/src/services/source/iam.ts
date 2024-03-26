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

import ApplyDataModel from '@services/model/iam/apply-data';

import http from '../http';

const path = '/apis/iam';

/**
 * 校验资源权限参数
 */
interface IAMParams {
  action_ids: Array<string>;
  resources?: Array<{ type: string; id?: string | number }>;
}

/**
 * 检查当前用户对该动作是否有权限
 */
export function checkAuthAllowed(params: IAMParams) {
  return http.post<
    {
      action_id: string;
      is_allowed: boolean;
    }[]
  >(`${path}/check_allowed/`, params);
}

export function simpleCheckAllowed(params: {
  action_id: string;
  resource_ids: Array<string | number>;
  bk_biz_id?: number;
}) {
  return http.post<boolean>(`${path}/simple_check_allowed/`, params);
}
/**
 * 获取权限申请数据
 */
export function getApplyDataLink(params: IAMParams) {
  return http.post<ApplyDataModel>(`${path}/get_apply_data/`, params).then((data) => new ApplyDataModel(data));
}

export function simpleGetApplyData(params: {
  action_id: string;
  resource_ids: Array<string | number>;
  bk_biz_id?: number;
}) {
  return http
    .post<ApplyDataModel>(`${path}/simple_get_apply_data/`, {
      ...params,
    })
    .then((data) => new ApplyDataModel(data));
}
