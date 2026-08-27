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
    class="dbm-tag"
    :class="{
      'is-checkable': checkable,
      'is-checked': checked,
      'is-closable': closable,
      'is-danger': theme === 'danger',
      'is-filled': type === 'filled',
      'is-info': theme === 'info',
      'is-small': size === 'small',
      'is-stroke': type === 'stroke',
      'is-success': theme === 'success',
      'is-warning': theme === 'warning',
    }"
    :style="{ borderRadius: radius }"
    @click="handleClick">
    <span
      v-if="$slots.icon"
      class="dbm-tag-icon">
      <slot name="icon" />
    </span>
    <span
      ref="textRef"
      v-bk-tooltips="{
        content: overflowTips,
        disabled: !overflowTips,
        extCls: 'dbm-tag-tooltips',
      }"
      class="dbm-tag-text">
      <slot />
    </span>
    <!-- bkui-vue 图标里 Error 才是纯 ×，Close 是带圆圈的 ×，此处与 bk-tag 保持一致用 Error -->
    <Error
      v-if="closable"
      class="dbm-tag-close"
      @click="handleClose" />
  </div>
</template>

<script setup lang="ts">
  import { Error } from 'bkui-vue/lib/icon';
  import type { VNode } from 'vue';

  interface Props {
    checkable?: boolean;
    checked?: boolean;
    closable?: boolean;
    radius?: string;
    size?: 'small' | 'default';
    stopPropagation?: boolean;
    theme?: '' | 'success' | 'info' | 'warning' | 'danger';
    type?: '' | 'filled' | 'stroke';
  }

  interface Emits {
    (e: 'change', checked: boolean): void;
    (e: 'close', event: MouseEvent): void;
  }

  defineOptions({
    name: 'Tag',
  });

  const props = withDefaults(defineProps<Props>(), {
    checkable: false,
    checked: false,
    closable: false,
    radius: '2px',
    size: 'default',
    stopPropagation: true,
    theme: '',
    type: '',
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    default?: () => VNode;
    icon?: () => VNode;
  }>();

  const textRef = ref<HTMLElement>();
  const overflowTips = ref('');

  const handleClick = (event: MouseEvent) => {
    event.preventDefault();
    if (props.stopPropagation) {
      event.stopPropagation();
    }
    if (props.checkable) {
      emits('change', !props.checked);
    }
  };

  const handleClose = (event: MouseEvent) => {
    event.preventDefault();
    if (props.stopPropagation) {
      event.stopPropagation();
    }
    emits('close', event);
  };

  onMounted(() => {
    const resizeObserver = new ResizeObserver(() => {
      const textEl = textRef.value!;
      overflowTips.value = textEl.scrollWidth > textEl.clientWidth ? textEl.innerText : '';
    });
    resizeObserver.observe(textRef.value!);

    onBeforeUnmount(() => {
      resizeObserver.unobserve(textRef.value!);
      resizeObserver.disconnect();
    });
  });
</script>

<style lang="less">
  .dbm-tag {
    display: inline-flex;
    height: 22px;
    max-width: 100%;
    padding: 0 8px;
    font-size: 12px;
    line-height: 22px;
    color: #63656e;
    cursor: default;
    background-color: #f0f1f5;
    border-color: #979ba54d;
    box-sizing: border-box;
    align-items: center;

    & ~ .dbm-tag {
      margin-left: 4px;
    }

    &:hover {
      background-color: #dcdee5;
    }

    &.is-filled {
      color: #fff;
      background-color: #979ba5;

      &:hover {
        background-color: #acafb6;
      }
    }

    &.is-stroke {
      padding: 0 9px;
      line-height: 20px;
      border-style: solid;
      border-width: 1px;
    }

    &.is-closable {
      padding: 0 4px 0 10px;
    }

    &.is-checkable {
      cursor: pointer;
      background: none;

      &:hover {
        background: #f0f1f5;
      }
    }

    &.is-checked {
      color: #fff;
      background: #3a84ff;

      &:hover {
        color: #fff;
        background: #3a84ff;
      }
    }

    &.is-small {
      height: 16px;
      padding: 0 4px;
      line-height: 16px;

      .dbm-tag-text {
        font-size: 10px;
      }
    }

    &.is-success {
      color: #14a568;
      background-color: #e4faf0;
      border-color: #14a5684d;

      &:hover:not(.is-filled) {
        background-color: #c9f5e2;
      }

      &.is-filled {
        color: #fff;
        background-color: #14a568;

        &:hover {
          background-color: #42b685;
        }
      }
    }

    &.is-info {
      color: #3a84ff;
      background-color: #edf4ff;
      border-color: #3a84ff4d;

      &:hover:not(.is-filled) {
        background-color: #e1ecff;
      }

      &.is-filled {
        color: #fff;
        background-color: #3a84ff;

        &:hover {
          background-color: #609cfe;
        }
      }
    }

    &.is-warning {
      color: #fe9c00;
      background-color: #fff1db;
      border-color: #fea5004d;

      &:hover:not(.is-filled) {
        background-color: #ffe8c3;
      }

      &.is-filled {
        color: #fff;
        background-color: #fe9c00;

        &:hover {
          background-color: #fdaf32;
        }
      }
    }

    &.is-danger {
      color: #ea3636;
      background-color: #feebea;
      border-color: #ea35364d;

      &:hover:not(.is-filled) {
        background-color: #fedddc;
      }

      &.is-filled {
        color: #fff;
        background-color: #ea3536;

        &:hover {
          background-color: #ed5c5d;
        }
      }
    }

    .dbm-tag-icon {
      margin-right: 4px;
      font-size: 14px;
      line-height: 0;
      flex-shrink: 0;
    }

    .dbm-tag-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex: 1;
    }

    .dbm-tag-close {
      margin-left: 4px;
      font-size: 12px;
      line-height: 0;
      cursor: pointer;
      flex-shrink: 0;
    }
  }

  .tippy-box.dbm-tag-tooltips {
    max-width: 500px;
    word-break: break-all;
  }
</style>
