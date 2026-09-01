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
  <div class="bk-editable-textarea">
    <div
      v-if="slots.prepend"
      class="bk-editable-textarea-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <DbmInput
      v-model="modelValue"
      autosize
      clearable
      :resize="false"
      v-bind="{ ...attrs, ...props }"
      :rows="rows ?? 1"
      type="textarea"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus" />
    <div
      v-if="slots.append"
      class="bk-editable-textarea-append-wrapper">
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
    rows?: number;
  }

  interface Emits {
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    append?: () => VNode;
    default?: () => VNode;
    prepend?: () => VNode;
  }>();

  const modelValue = defineModel<string>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const handleBlur = () => {
    columnContext?.blur();
    columnContext?.validate('blur');
    emits('blur');
  };

  const handleFocus = () => {
    columnContext?.focus();
    emits('focus');
  };

  const handleChange = (value: string) => {
    emits('change', value);
  };
</script>
<style lang="less">
  .bk-editable-table-body-column {
    &.is-readonly,
    &.is-disabled {
      .bk-editable-textarea {
        .dbm-textarea {
          pointer-events: none;

          .dbm-input-suffix-icon {
            display: none !important;
          }

          * {
            pointer-events: none;
          }
        }
      }
    }
  }

  .bk-editable-textarea {
    position: relative;
    display: flex;
    width: 100%;
    padding-top: 6px;
    padding-bottom: 6px;
    overflow: hidden;

    .dbm-textarea {
      background: transparent;
      border: none;
      border-radius: 0;
      box-shadow: none !important;
      flex-direction: row;

      textarea {
        background: transparent;
      }

      .dbm-input-suffix-icon {
        align-items: center;
      }

      .dbm-textarea-clear-icon {
        top: 7px;
        right: 0;
        bottom: 7px;
        min-height: 14px;
        align-items: center;
      }
    }
  }

  .bk-editable-textarea-prepend-wrapper,
  .bk-editable-textarea-append-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 8px;
    user-select: none;
  }

  .bk-editable-textarea-prepend-wrapper {
    padding-left: 10px;
  }

  .bk-editable-textarea-append-wrapper {
    padding-right: 10px;
    margin-left: auto;
  }
</style>
