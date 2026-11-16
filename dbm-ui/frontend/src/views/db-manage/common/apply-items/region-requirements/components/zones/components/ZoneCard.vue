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
  <div
    class="zone-card"
    :class="{ 'is-selected': selected }"
    @click="emit('select')">
    <div class="zone-card-title">{{ title }}</div>
    <div
      v-if="displaySubzones.length > 0"
      class="zone-card-subzones">
      <span>{{ displaySubzones.join('，') }}</span>
      <BkPopover
        v-if="overflowCount > 0"
        placement="top"
        theme="light">
        <span class="zone-card-count ml-4">{{ t('共 {n} 个', { n: subzones!.length }) }}</span>
        <template #content>
          <div class="zone-card-count-popover">
            <div class="zone-card-count-title mb-4">{{ t('全部园区（{n}）', { n: subzones!.length }) }}</div>
            <div
              v-for="subzoneItem in subzones!"
              :key="subzoneItem"
              class="zone-card-count-item">
              {{ subzoneItem }}
            </div>
          </div>
        </template>
      </BkPopover>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    selected?: boolean;
    /** 该可用区下登记过的全部园区全称，无园区时不渲染第二行 */
    subzones?: string[];
    /** 卡片标题：可用区名或「随机」 */
    title: string;
  }

  type Emits = (e: 'select') => void;

  const props = defineProps<Props>();

  const emit = defineEmits<Emits>();

  const { t } = useI18n();

  /** 第二行最多展示 3 个园区，超出追加「共 N 个」并悬停展示全部 */
  const maxDisplayCount = 3;

  const displaySubzones = computed(() => (props.subzones || []).slice(0, maxDisplayCount));

  const overflowCount = computed(() => {
    const { subzones } = props;
    if (!subzones || subzones.length <= maxDisplayCount) {
      return 0;
    }
    return subzones.length;
  });
</script>

<style lang="less" scoped>
  .zone-card {
    min-width: 168px;
    padding: 8px 12px;
    cursor: pointer;
    background: #fff;
    border: 1px solid #dcdee5;
    border-radius: 4px;
    transition: border-color 0.12s ease;

    &:hover {
      border-color: #c4c6cc;
    }

    &.is-selected {
      background: #f0f5ff;
      border-color: #3a84ff;

      .zone-card-title {
        color: #3a84ff;
      }
    }

    .zone-card-title {
      overflow: hidden;
      font-size: 12px;
      line-height: 24px;
      // font-weight: bolder;
      color: #313238;
      // text-overflow: ellipsis;
      // white-space: nowrap;
    }

    .zone-card-subzones {
      // margin-top: 4px;
      overflow: hidden;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      text-overflow: ellipsis;
      white-space: nowrap;

      .zone-card-count {
        color: #63656e;
        cursor: pointer;
        border-bottom: 1px dashed #63656e;
      }
    }
  }

  .zone-card-count-popover {
    max-height: 240px;
    overflow: auto;

    .zone-card-count-title {
      font-weight: bolder;
      color: #979ba5;
    }

    .zone-card-count-item {
      padding: 2px 0;
    }
  }
</style>
