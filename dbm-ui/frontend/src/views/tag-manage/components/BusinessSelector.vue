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
    v-model="selected"
    :min-height="389"
    @toggle="handleToggle">
    <template #trigger>
      <slot name="trigger">
        <div
          ref="businessSelectorRef"
          class="business-selector">
          <div>{{ bizIdMap.get(selected as number)?.name }}</div>
          <AngleDownFill
            class="triangle-icon mt-2 ml-7"
            :class="[{ rotate: !isExpanded }]" />
        </div>
      </slot>
    </template>
    <BkOption
      v-for="item in sortedBizList"
      :key="item.bk_biz_id"
      :label="`${item.name}(#${item.bk_biz_id}, ${item.english_name})`"
      :value="item.bk_biz_id">
      {{ `${item.name}` }}
      <span class="biz-info">
        {{ `(#${item.bk_biz_id}${item.english_name ? `, ${item.english_name}` : ''})` }}
      </span>
      <div style="margin-left: auto">
        <DbIcon
          v-if="favorBizIdSet.has(item.bk_biz_id)"
          class="favored"
          style="color: #ffb848"
          type="star-fill"
          @click.stop="() => handleUnfavor(item.bk_biz_id)" />
        <DbIcon
          v-else
          class="unfavored"
          type="star"
          @click.stop="() => handleFavor(item.bk_biz_id)" />
      </div>
    </BkOption>
  </BkSelect>
</template>

<script setup lang="tsx">
  import { AngleDownFill } from 'bkui-vue/lib/icon';
  import { cloneDeep } from 'lodash';
  import { defineEmits, ref } from 'vue';

  import { getProfile, upsertProfile } from '@services/source/profile';

  import { useGlobalBizs, useUserProfile } from '@stores';

  interface Emits {
    (e: 'change', value: number): void;
  }

  const emits = defineEmits<Emits>();

  const { bizs: bizList, currentBizInfo, bizIdMap } = useGlobalBizs();
  const userStore = useUserProfile();

  const favorBizIdSet = ref<Set<number>>(new Set());
  const selected = ref(currentBizInfo?.bk_biz_id);
  const isExpanded = ref(false);

  const sortedBizList = computed(() => {
    const clonedBizList = cloneDeep(bizList);

    return clonedBizList.sort((item1, item2) => {
      const isItem1Favored = favorBizIdSet.value.has(item1.bk_biz_id) ? 1 : 0;
      const isItem2Favored = favorBizIdSet.value.has(item2.bk_biz_id) ? 1 : 0;

      return isItem2Favored - isItem1Favored;
    });
  });

  watch(selected, () => {
    emits('change', selected.value as number);
  });

  watch(
    () => userStore.profile,
    (profile) => {
      favorBizIdSet.value = new Set(profile.APP_FAVOR.map((bizId: string) => +bizId));
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleFavor = (bkBizId: number) => {
    favorBizIdSet.value.add(bkBizId);
    updateUserFavor(favorBizIdSet.value);
  };

  const handleUnfavor = (bkBizId: number) => {
    favorBizIdSet.value.delete(bkBizId);
    updateUserFavor(favorBizIdSet.value);
  };

  const updateUserFavor = async (set: Set<number>) => {
    await upsertProfile({
      label: 'APP_FAVOR',
      values: Array.from(set).map((bizId: number) => String(bizId)),
    });
    getProfile();
  };

  const handleToggle = () => {
    isExpanded.value = !isExpanded.value;
  };
</script>

<style lang="less" scoped>
  .business-selector {
    display: flex;
    width: 360px;
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
    align-items: center;

    .triangle-icon {
      transition: transform 0.2s ease; // 确保过渡效果应用到 transform
    }

    .rotate {
      transform: rotate(180deg); // 旋转180度
    }
  }

  .bk-select-option {
    .biz-info {
      margin-left: 2px;
      color: #979ba5;
    }

    .unfavored {
      visibility: hidden;
    }

    &:hover {
      .unfavored {
        visibility: visible;
      }
    }
  }
</style>
