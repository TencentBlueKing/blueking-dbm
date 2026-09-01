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
  <div class="bk-editable-input">
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
<script setup lang="ts">
  import { useAttrs, type VNode, watch } from 'vue';

  import DbmInput from '@components/bkui-vue/input/Index.vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    maxlength?: number;
    minlength?: number;
    placeholder?: string;
    prefix?: string;
    suffix?: string;
  }

  interface Emits {
    (e: 'blur' | 'focus'): void;
    (e: 'change', params: string): void;
  }

  interface Exposes {
    focus(): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    append?: () => VNode;
    default?: () => VNode;
    prepend?: () => VNode;
  }>();

  const modelValue = defineModel<string | number>();

  const attrs = useAttrs();
  const columnContext = useColumn();

  const inputRef = ref();

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const handleChange = (value: string) => {
    emits('change', value);
  };

  const handleBlur = () => {
    columnContext?.blur();
    columnContext?.validate('blur');
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
          .dbm-textarea-clear-icon {
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
