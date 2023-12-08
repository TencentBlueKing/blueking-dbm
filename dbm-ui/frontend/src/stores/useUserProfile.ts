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

import { defineStore } from 'pinia';

import {
  getProfile,
  upsertProfile,
} from '@services/source/profile';

// import { UserPersonalSettings } from '@common/const';

type ProfileItem = ServiceReturnType<typeof getProfile>['profile'][number]

interface State {
  globalManage: boolean,
  profile: Record<string, any>,
  isManager: boolean,
  rerourceManage: boolean,
  username: string,
}

/**
 * 获取系统个人配置信息
 */
export const useUserProfile = defineStore('UserProfile', {
  state: (): State => ({
    globalManage: false,
    profile: {} as State['profile'],
    isManager: false,
    rerourceManage: false,
    username: '',
  }),
  actions: {
    /**
     * 获取个人配置列表
     */
    fetchProfile() {
      return getProfile()
        .then((result) => {
          this.globalManage = Boolean(result.global_manage);
          this.rerourceManage = Boolean(result.resource_manage);
          this.username = result.username;
          this.isManager = result.is_manager;

          this.profile = result.profile.reduce((result, item) => Object.assign(result, {
            [item.label]: item.values,
          }), {} as State['profile']);

          return result;
        });
    },

    /**
     * 更新个人配置信息
     */
    updateProfile(params: ProfileItem) {
      return upsertProfile(params)
        .then(() => this.fetchProfile());
    },
  },
});
