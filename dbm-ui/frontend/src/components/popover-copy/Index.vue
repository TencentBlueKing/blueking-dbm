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
  <div class="dbm-popover-copy">
    <DbIcon
      ref="copyRootRef"
      :class="{ 'is-active': isActive }"
      type="copy" />
    <div style="display: none">
      <div
        ref="popRef"
        class="dbm-popover-copy-panel">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';

  let tippyIns: Instance;
  const isActive = ref(false);
  const copyRootRef = ref();
  const popRef = ref();

  onMounted(() => {
    nextTick(() => {
      tippyIns = tippy(copyRootRef.value.$el as SingleTarget, {
        content: popRef.value,
        placement: 'top',
        appendTo: () => document.body,
        theme: 'light',
        maxWidth: 'none',
        trigger: 'mouseenter click',
        interactive: true,
        arrow: false,
        allowHTML: true,
        zIndex: 999999,
        hideOnClick: true,
        onShow() {
          isActive.value = true;
        },
        onHide() {
          isActive.value = false;
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
  .dbm-popover-copy {
    display: inline-block;
    color: #3a84ff;

    .is-active {
      display: inline-block !important;
    }
  }

  .dbm-popover-copy-panel {
    & > * {
      position: relative;
      display: inline-block;
      padding: 0 4px;
      font-size: 12px;
      line-height: 24px;
      color: #3a84ff;
      vertical-align: middle;
      cursor: pointer;
      border-radius: 2px;

      &:hover {
        background-color: #f0f1f5;
      }

      &:nth-child(n + 2) {
        margin-left: 9px;

        &::before {
          position: absolute;
          top: 3px;
          left: -5px;
          display: inline-block;
          width: 1px;
          height: 18px;
          vertical-align: middle;
          background-color: #f0f1f5;
          content: '';
        }
      }
    }
  }
</style>
