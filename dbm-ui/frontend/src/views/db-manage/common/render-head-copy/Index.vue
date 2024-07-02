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
  <span
    @mouseout="() => (isCopyDropdown = false)"
    @mouseover="() => (isCopyDropdown = true)">
    <slot />
  </span>
  <BkDropdown
    class="ml-4 render-head-copy"
    @hide="() => (isCopyDropdown = false)"
    @show="() => (isCopyDropdown = true)">
    <DbIcon
      :class="{ active: isCopyDropdown }"
      type="copy" />
    <template #content>
      <BkDropdownMenu>
        <div
          v-for="item in config"
          :key="item.field">
          <BkDropdownItem>
            <BkButton
              v-bk-tooltips="{
                disabled: hasSelected,
                content: t('请先勾选'),
                placement: 'right',
              }"
              :disabled="!hasSelected"
              text
              @click="handleCopySelected(item.field)">
              {{ `${t('复制已选')}${item?.label ?? ''}` }}
            </BkButton>
          </BkDropdownItem>
          <BkDropdownItem>
            <BkButton
              text
              @click="handleCopyAll(item.field)">
              {{ `${t('复制所有')}${item?.label ?? ''}` }}
            </BkButton>
          </BkDropdownItem>
        </div>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script setup lang="ts" generic="T">
  import { useI18n } from 'vue-i18n';

  interface CopyItem {
    label?: string;
    field: keyof T;
  }

  interface Props {
    hasSelected: boolean;
    config: CopyItem[];
  }

  interface Emits {
    (e: 'handleCopySelected', field: keyof T): void;
    (e: 'handleCopyAll', field: keyof T): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isCopyDropdown = ref(false);

  const handleCopySelected = (field: keyof T) => {
    emits('handleCopySelected', field);
  };
  const handleCopyAll = (field: keyof T) => {
    emits('handleCopyAll', field);
  };
</script>

<style lang="less" scoped>
  .render-head-copy {
    .db-icon-copy {
      color: @primary-color;
      cursor: pointer;
      visibility: hidden;
    }

    .active {
      visibility: visible;
    }

    &:hover {
      .db-icon-copy {
        visibility: visible;
      }
    }

    .bk-dropdown-item {
      padding: 0;

      .bk-button {
        height: 100%;
        padding: 0 16px;
      }
    }
  }
</style>
