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

import { getBizs } from '@services/source/cmdb';
import type { BizItem } from '@services/types';

import { useUserProfile } from '@stores';

import { UserPersonalSettings } from '@common/const';

export const useGlobalBizs = defineStore('GlobalBizs', {
  state: () => ({
    bizs: [] as BizItem[],
    loading: false,
    currentBizId: 0,
    isError: false,
  }),
  getters: {
    currentBizInfo: (state): BizItem | undefined => state.bizs.find(item => item.bk_biz_id === state.currentBizId),
  },
  actions: {
    /**
     * 判断是否存在业务且有业务权限
     * @param bizId 业务 ID
     * @returns boolean | undefined
     */
    hasBizPermission(bizId: number) {
      const targetBizItem = this.bizs.find(item => item.bk_biz_id === bizId);
      return targetBizItem && targetBizItem.permission.db_manage;
    },
    /**
     * 获取全局业务列表
     */
    async fetchBizs() {
      const userProfileStore = useUserProfile();

      // 获取最新用户个人配置
      try {
        await userProfileStore.fetchProfile();
      } catch (e) {
        console.log(e);
      }

      const activatedBizId = userProfileStore.profile[UserPersonalSettings.ACTIVATED_APP];
      const favors = userProfileStore.profile[UserPersonalSettings.APP_FAVOR] || [];
      // 获取业务列表
      this.loading = true;
      await getBizs()
        .then((res) => {
          this.bizs = res;
          this.isError = false;
          const len = this.bizs.length;
          const pathBizId = Number(location.pathname.split('/')[2]);
          if (Number.isInteger(pathBizId)) {
            this.currentBizId = pathBizId;
            return;
          }
          // 用户上次选中的业务
          if (len > 0 && activatedBizId && this.hasBizPermission(activatedBizId)) {
            this.currentBizId = activatedBizId;
            return;
          }

          // 默认选中收藏第一个
          if (favors.length > 0) {
            for (const id of favors) {
              // 判断收藏业务是否存在于业务列表中
              if (this.hasBizPermission(Number(id))) {
                this.currentBizId = Number(id);
                return;
              }
            }
            return;
          }

          // 默认选中第一个
          const [first] = this.bizs;
          if (first && this.hasBizPermission(first.bk_biz_id)) {
            this.currentBizId = first.bk_biz_id;
          }
        })
        .catch(() => {
          this.isError = true;
        })
        .finally(() => {
          this.loading = false;
        });
    },
    changeBizId(id: number) {
      this.currentBizId = id;
    },
  },
});

