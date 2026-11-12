<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    class="bk-editable-input"
    :class="attrs.class">
    <div
      v-if="slots.prepend"
      class="bk-editable-input-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <DbmInput
      ref="inputRef"
      v-model="modelValue"
      clearable
      v-bind="{ ...attrs, ...props }"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus" />
    <div
      v-if="slots.append"
      class="bk-editable-input-append-wrapper">
      <slot name="append" />
    </div>
  </div>
</template>
<script setup lang="ts" generic="T extends string | number">
  import type { VNode } from 'vue';

  import DbmInput from '@components/bkui-vue/input/Index.vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  export interface Props {
    maxlength?: number;
    minlength?: number;
    placeholder?: string;
    prefix?: string;
    suffix?: string;
  }

  export interface Emits<T> {
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }

  export interface Exposes {
    focus(): void;
  }

  defineOptions({
    // 根节点是外层 div，attrs 已显式绑给 DbmInput；
    // 不关掉默认透传，未声明的监听（如 paste）会在根节点和 DbmInput 上各触发一次
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const emits = defineEmits<Emits<T>>();

  const slots = defineSlots<{
    append?: () => VNode;
    default?: () => VNode;
    prepend?: () => VNode;
  }>();

  const modelValue = defineModel<T | undefined>({
    default: undefined,
  });

  const attrs = useAttrs();
  const columnContext = useColumn();

  const inputRef = ref();

  watch(modelValue, () => {
    // 校验不通过会 reject(false)，这里只触发校验并展示错误态，不处理结果（下方 blur 同理）
    columnContext?.validate('change').catch(() => {});
  });

  const handleChange = (value: T) => {
    emits('change', value);
  };

  const handleBlur = () => {
    columnContext?.blur();
    columnContext?.validate('blur').catch(() => {});
    emits('blur');
  };

  const handleFocus = () => {
    columnContext?.focus();
    emits('focus');
  };

  defineExpose<Exposes>({
    focus() {
      inputRef.value?.focus();
    },
  });
</script>
<style lang="less">
  .bk-editable-table-body-column {
    &.is-readonly,
    &.is-disabled {
      .bk-editable-input {
        .dbm-input {
          .dbm-input-clear-icon {
            display: none !important;
          }

          * {
            pointer-events: none;
          }
        }
      }
    }
  }

  .bk-editable-input {
    position: relative;
    display: flex;
    width: 100%;
    overflow: hidden;

    .dbm-input {
      height: 40px;
      background: transparent;
      border: none;
      box-shadow: none !important;

      .dbm-input-text {
        background: transparent;
      }

      .dbm-input-suffix-icon {
        background: transparent;
      }
    }
  }

  .bk-editable-input-prepend-wrapper,
  .bk-editable-input-append-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 8px;
    user-select: none;
  }

  .bk-editable-input-prepend-wrapper {
    padding-left: 10px;
  }

  .bk-editable-input-append-wrapper {
    padding-right: 10px;
    margin-left: auto;
  }
</style>
