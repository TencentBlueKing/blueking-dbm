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
  <span class="render-head-copy">
    <slot />
    <DbIcon
      ref="copyRootRef"
      :class="{ 'is-active': isCopyIconClicked }"
      type="copy" />
  </span>
  <div style="display: none">
    <div
      ref="popRef"
      class="dropdownmenu">
      <ul
        v-for="item in config"
        :key="item.field">
        <li class="dropdownmenu-item">
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
        </li>
        <li class="dropdownmenu-item">
          <BkButton
            text
            @click="handleCopyAll(item.field)">
            {{ `${t('复制所有')}${item?.label ?? ''}（${isFilter ? t('筛选后') : t('全量')}）` }}
          </BkButton>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  export interface Props<T> {
    hasSelected: boolean;
    config: {
      label?: string;
      field: keyof T;
    }[];
    isFilter: boolean;
  }

  export interface Emits<T> {
    (e: 'handleCopySelected', field: keyof T): void;
    (e: 'handleCopyAll', field: keyof T): void;
  }

  defineProps<Props<T>>();

  const emits = defineEmits<Emits<T>>();

  const { t } = useI18n();

  let tippyIns: Instance;
  const isCopyIconClicked = ref(false);
  const copyRootRef = ref();
  const popRef = ref();

  const handleCopySelected = (field: keyof T) => {
    emits('handleCopySelected', field);
  };
  const handleCopyAll = (field: keyof T) => {
    emits('handleCopyAll', field);
  };

  onMounted(() => {
    nextTick(() => {
      tippyIns = tippy(copyRootRef.value.$el as SingleTarget, {
        content: popRef.value,
        placement: 'bottom',
        appendTo: () => document.body,
        theme: 'light db-dropdownmenu-theme',
        maxWidth: 'none',
        trigger: 'mouseenter click',
        interactive: true,
        arrow: false,
        allowHTML: true,
        zIndex: 999,
        hideOnClick: true,
        onShow() {
          isCopyIconClicked.value = true;
        },
        onHide() {
          isCopyIconClicked.value = false;
        },
      });
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });
</script>

<style lang="less">
  .render-head-copy {
    .db-icon-copy {
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }

    .is-active {
      display: inline-block;
    }
  }

  .tippy-box[data-theme~='db-dropdownmenu-theme'] {
    background-color: #fff;
    border: 1px solid #dcdee5 !important;
    border-radius: 2px !important;
    box-shadow: 0 2px 6px 0 #0000001a !important;

    .tippy-content {
      padding: 4px 0;
      background-color: #fff;
    }
  }

  .dropdownmenu {
    .dropdownmenu-item {
      height: 32px;
      padding: 0 16px;
      font-size: 12px;
      line-height: 33px;
      color: #63656e;
      white-space: nowrap;
      list-style: none;
      cursor: pointer;

      &:hover {
        background: #f5f7fa;
      }
    }
  }
</style>
