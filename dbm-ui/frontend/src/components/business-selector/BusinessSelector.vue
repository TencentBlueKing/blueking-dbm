<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSelect
    class="business-selector"
    filterable
    :input-search="false"
    :loading="isLoading"
    v-bind="$attrs">
    <AuthComponent
      v-for="item in renderList"
      :key="item.bk_biz_id"
      action-id="DB_MANAGE"
      :permission="item.permission.db_manage"
      :resource-id="item.bk_biz_id"
      resource-type="BUSINESS">
      <BkOption
        :label="item.display_name"
        :value="item.bk_biz_id">
        <div class="business-selector-item">
          <span
            v-overflow-tips
            class="business-selector-display text-overflow">
            {{ item.display_name }}
          </span>
          <i
            class="business-selector-favor"
            :class="[favorIds.includes(item.bk_biz_id) ? 'db-icon-star-fill' : 'db-icon-star']"
            @click.stop="handleFavor(item)" />
        </div>
      </BkOption>
      <template #forbid>
        <BkOption
          disabled
          :label="item.display_name"
          :value="item.bk_biz_id" />
      </template>
    </AuthComponent>
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getBizs } from '@services/common';
  import type { BizItem } from '@services/types/common';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { messageSuccess } from '@utils';

  const userProfileStore = useUserProfile();
  const { t } = useI18n();

  // 确保是最新的个人配置
  userProfileStore.fetchProfile();

  const favors = computed(() => userProfileStore.profile[UserPersonalSettings.APP_FAVOR] || []);
  const favorIds = computed(() => favors.value.map((bizId: string) => Number(bizId)));

  const isLoading = ref(false);
  const bizList = shallowRef<BizItem[]>([]);
  const renderList = computed(() => {
    const favorList: BizItem[] = [];
    const unfavorList: BizItem[] = [];

    for (const biz of bizList.value) {
      const id = String(biz.bk_biz_id);
      if (favors.value.includes(id)) {
        favorList.push(biz);
      } else {
        unfavorList.push(biz);
      }
    }

    return [...favorList, ...unfavorList];
  });

  /**
   * 获取业务列表
   */
  const fetchBizs = () => {
    isLoading.value = true;
    getBizs()
      .then((res) => {
        bizList.value = res;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
  fetchBizs();

  const handleFavor = (info: BizItem) => {
    const id = String(info.bk_biz_id);
    const index = favors.value.findIndex((key: string) => key === id);
    const isFavored = index > -1;
    const params = {
      label: UserPersonalSettings.APP_FAVOR,
      values: favors.value,
    };
    if (isFavored) {
      params.values.splice(index, 1);
    } else {
      params.values.push(id);
    }
    userProfileStore.updateProfile(params)
      .then(() => {
        messageSuccess(isFavored ? t('取消收藏成功') : t('收藏成功'));
      });
  };
</script>

<style lang="less" scoped>
.business-selector {
  &-item {
    flex: 1;
    display: flex;
    align-items: center;

    &:hover {
      .business-selector-favor {
        display: block;
      }
    }
  }

  &-display {
    flex: 1;
  }

  &-favor {
    flex-shrink: 0;
    display: none;

    &.db-icon-star-fill {
      display: block;
      color: @warning-color;
    }
  }
}
</style>
