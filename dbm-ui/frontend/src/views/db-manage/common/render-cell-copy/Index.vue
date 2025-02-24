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
  <div class="render-cell-copy">
    <DbIcon
      ref="copyRootRef"
      :class="{ 'is-active': isCopyIconClicked }"
      type="copy" />
    <div style="display: none">
      <div ref="popRef">
        <span
          v-for="(item, index) in copyItems"
          :key="item.value">
          <span
            v-if="index !== 0"
            class="copy-trigger-split" />
          <BkButton
            class="copy-trigger"
            text
            theme="primary"
            @click="copy(item.value)">
            {{ `${t('复制')}${item.label}` }}
          </BkButton>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  interface Props {
    copyItems: {
      label: string;
      value: string;
    }[];
  }

  defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();

  let tippyIns: Instance;
  const isCopyIconClicked = ref(false);
  const copyRootRef = ref();
  const popRef = ref();

  onMounted(() => {
    nextTick(() => {
      tippyIns = tippy(copyRootRef.value.$el as SingleTarget, {
        allowHTML: true,
        appendTo: () => document.body,
        arrow: false,
        content: popRef.value,
        hideOnClick: true,
        interactive: true,
        maxWidth: 'none',
        onHide() {
          isCopyIconClicked.value = false;
        },
        onShow() {
          isCopyIconClicked.value = true;
        },
        placement: 'top',
        theme: 'light',
        trigger: 'mouseenter click',
        zIndex: 999999,
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

<style lang="less" scoped>
  .render-cell-copy {
    display: grid;
    color: #3a84ff;

    .is-active {
      display: inline-block !important;
    }
  }

  .copy-trigger {
    display: inline-block;
    padding: 0 4px;
    font-size: 12px;
    line-height: 24px;
    vertical-align: middle;
    border-radius: 2px;

    &:hover {
      background-color: #f0f1f5;
    }
  }

  .copy-trigger-split {
    display: inline-block;
    width: 1px;
    height: 18px;
    margin: 0 4px;
    vertical-align: middle;
    background-color: #f0f1f5;
  }
</style>
