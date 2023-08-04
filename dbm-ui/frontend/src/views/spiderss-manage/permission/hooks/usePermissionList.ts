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

import { getPermissionList } from '@services/spider/permission';

import { AccountTypes } from '@common/const';

import { getSearchSelectorParams } from '@utils';

import type { PermissionState } from '../common/types';

export const usePermissionList = (state: PermissionState) => {
  const getList = () => {
    state.isLoading = true;
    getPermissionList({
      ...getSearchSelectorParams(state.search),
      account_type: AccountTypes.TENDBCLUSTER,
    })
      .then((res) => {
        state.data = res.results.map(item => Object.assign({ isExpand: true }, item));
        state.isAnomalies = false;
      })
      .catch(() => {
        state.data = [];
        state.isAnomalies = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  return {
    getList,
  };
};
