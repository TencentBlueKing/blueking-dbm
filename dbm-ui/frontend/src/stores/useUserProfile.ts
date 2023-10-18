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

import { getProfile, upsertProfile } from '@services/common';
import type { ProfileItem } from '@services/types/common';

interface ProfileMap {
  [key: string]: any
}

interface State {
  username: string,
  profile: ProfileMap,
  isManager: boolean
}

/**
 * 获取系统个人配置信息
 */
export const useUserProfile = defineStore('UserProfile', {
  state: (): State => ({
    username: '',
    isManager: false,
    profile: {},
  }),
  actions: {
    /**
     * 获取个人配置列表
     */
    fetchProfile() {
      return getProfile().then((res) => {
        const { username = '', profile = [] } = res;
        this.username = username;
        this.isManager = res.is_manager;
        if (profile.length > 0) {
          profile.forEach((item) => {
            this.profile[item.label] = item.values;
          });
        }
        return res;
      });
    },

    /**
     * 更新个人配置信息
     */
    updateProfile(params: ProfileItem) {
      return upsertProfile(params).then(() => this.fetchProfile());
    },
  },
});
