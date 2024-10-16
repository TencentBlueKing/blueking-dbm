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
      <div
        ref="businessSelectorRef"
        class="business-selector">
        <div>{{ bizIdMap.get(selected as number)?.name }}</div>
        <div
          ref="triangleRef"
          class="triangle"></div>
      </div>
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
  import { cloneDeep } from 'lodash';
  import { defineEmits, ref } from 'vue';

  import { useGlobalBizs } from '@stores';

  interface Emits {
    (e: 'change', value: number): void;
  }

  const emits = defineEmits<Emits>();

  const { bizs: bizList, currentBizInfo, bizIdMap } = useGlobalBizs();
  const triangleRef = useTemplateRef('triangleRef');

  const favorBizIdSet = ref<Set<number>>(new Set());
  const selected = ref(currentBizInfo?.bk_biz_id);

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

  const handleFavor = (bkBizId: number) => {
    favorBizIdSet.value.add(bkBizId);
  };

  const handleUnfavor = (bkBizId: number) => {
    favorBizIdSet.value.delete(bkBizId);
  };

  const handleToggle = () => {
    triangleRef.value?.classList.toggle('up');
  };
</script>

<style lang="less" scoped>
  .business-selector {
    cursor: pointer;
    color: #3a84ff;
    display: flex;
    align-items: center;
    font-size: 14px;
    width: 360px;

    .triangle {
      width: 0;
      height: 0;
      border-left: 4.875px solid transparent;
      border-right: 4.875px solid transparent;
      border-top: 6px solid #3a84ff;
      transition: transform 0.3s ease;
      margin-left: 7px;

      &.up {
        transform: rotate(180deg);
      }
    }
  }

  .bk-select-option {
    .biz-info {
      color: #979ba5;
      margin-left: 2px;
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
