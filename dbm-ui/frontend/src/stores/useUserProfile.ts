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

import { getProfile, upsertProfile } from '@services/source/profile';

type ProfileItem = ServiceReturnType<typeof getProfile>['profile'][number];

/**
 * 获取系统个人配置信息
 */
export const useUserProfile = defineStore('UserProfile', {
  state: () => ({
    globalManage: false, // 顶部导航全部配置访问权限
    isSuperuser: false, // 登录用户超级管理员权限
    isDba: false,
    platformManage: false,
    platformTicketView: false,
    platformTaskflowView: false,
    profile: {} as Record<string, any>,
    rerourceManage: false, // 顶部导航资源管理访问权限
    username: '',
  }),
  actions: {
    /**
     * 获取个人配置列表
     */
    fetchProfile() {
      return getProfile().then((result) => {
        this.globalManage = Boolean(result.global_manage);
        this.isSuperuser = result.is_superuser;
        this.isDba = Boolean(result.is_dba);
        this.platformManage = Boolean(result.platform_manage);
        this.platformTicketView = Boolean(result.platform_ticket_view);
        this.platformTaskflowView = Boolean(result.platform_taskflow_view);
        this.rerourceManage = Boolean(result.resource_manage);
        this.username = result.username;

        this.profile = result.profile.reduce(
          (result, item) =>
            Object.assign(result, {
              [item.label]: item.values,
            }),
          {},
        );

        return result;
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
