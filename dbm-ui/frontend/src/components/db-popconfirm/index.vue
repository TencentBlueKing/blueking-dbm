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
    ref="rootRef"
    v-bind="$attrs"
    class="db-popconfirm">
    <slot />
  </div>
  <div
    ref="popRef"
    style="width: 280px; padding: 15px 10px;">
    <div style="font-size: 16px; line-height: 20px; color: #313238;">
      {{ title }}
    </div>
    <div style="margin-top: 10px; font-size: 12px; color: #63656e;">
      {{ content }}
    </div>
    <div style="margin-top: 16px; text-align: right;">
      <BkButton
        class="mr8"
        :loading="isConfirmLoading"
        size="small"
        theme="primary"
        @click="handleConfirm">
        {{ $t('确认') }}
      </BkButton>
      <BkButton
        size="small"
        @click="handleCancel">
        {{ $t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script lang="ts">
  export default {
    name: 'DbPopconfirm',
  };
</script>
<script setup lang="ts">
  import tippy, {
    type Instance,
    type Placement,
    type SingleTarget,
  } from 'tippy.js';
  import {
    onBeforeUnmount,
    onMounted,
    ref,
  } from 'vue';

  interface Props {
    title: string,
    content: string,
    placement?: Placement,
    confirmHandler: () => Promise<any>,
    cancelHandler?: () => Promise<any>,
  }
  const props = withDefaults(defineProps<Props>(), {
    placement: 'top',
    cancelHandler: () => Promise.resolve(),
  });

  let tippyIns: Instance;

  const rootRef = ref();
  const popRef = ref();
  const isConfirmLoading = ref(false);

  const handleConfirm = () => {
    isConfirmLoading.value = true;
    Promise.resolve()
      .then(() => props.confirmHandler())
      .then(() => {
        tippyIns.hide();
      })
      .finally(() => {
        isConfirmLoading.value = false;
      });
  };

  const handleCancel = () => {
    Promise.resolve()
      .then(() => props.cancelHandler())
      .then(() => {
        tippyIns.hide();
      });
  };

  onMounted(() => {
    const tippyTarget = rootRef.value.children[0];
    if (tippyTarget) {
      tippyIns = tippy(tippyTarget as SingleTarget, {
        content: popRef.value,
        placement: props.placement,
        appendTo: () => document.body,
        theme: 'light db-popconfirm-theme',
        maxWidth: 'none',
        trigger: 'click',
        interactive: true,
        arrow: true,
        offset: [0, 12],
        zIndex: 999999,
        hideOnClick: true,
      });
    }
  });

  onBeforeUnmount(() => {
    tippyIns.hide();
    tippyIns.unmount();
    tippyIns.destroy();
  });
</script>
<style lang="less">
  .db-popconfirm {
    display: inline-block;
  }

  .tippy-box[data-theme~="db-popconfirm-theme"] {
    background-color: #fff;
    border: 1px solid #dcdee5 !important;
    border-radius: 2px !important;
    box-shadow: 0 0 6px 0 #dcdee5 !important;

    .tippy-content {
      background-color: #fff;
    }

    .tippy-arrow {
      position: absolute;
      bottom: -6px !important;
      left: 50% !important;
      background: #fff;
      border: 1px solid #dcdee5 !important;
      transform: translateX(-50%) rotateZ(45deg) !important;
      box-shadow: 0 0 6px 0 #dcdee5 !important;

      &::before {
        content: none;
      }
    }
  }
</style>
