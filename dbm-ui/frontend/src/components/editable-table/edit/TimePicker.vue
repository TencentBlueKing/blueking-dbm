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
  <BkTimePicker
    v-model="modelValue"
    append-to-body
    class="bk-editable-time-picker"
    v-bind="{ ...attrs, ...props }"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus" />
</template>
<script lang="ts">
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    disabledDate?: (date: Date | number) => boolean;
    format?: string;
    multiple?: boolean;
    placeholder?: string;
    type?: 'time' | 'timerange';
  }
</script>
<script setup lang="ts" generic="T extends [string, string] | [Date, Date] | string | Date">
  import { useAttrs, watch } from 'vue';

  import useColumn from '../useColumn';

  const props = defineProps<Props>();
  const emits = defineEmits<{
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }>();

  const modelValue = defineModel<T>();

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

  const handleChange = (value: T) => {
    emits('change', value);
  };
</script>
<style lang="less">
  .bk-editable-table-body-column {
    &.is-readonly,
    &.is-disabled {
      .bk-editable-time-picker {
        .bk-date-picker {
          pointer-events: none;

          .clear-action {
            display: none !important;
          }

          * {
            pointer-events: none;
          }
        }
      }
    }
  }

  .bk-editable-time-picker {
    &.bk-date-picker {
      width: 100%;

      .icon-wrapper {
        height: 40px;
      }

      .bk-date-picker-editor {
        height: 40px;
        background: transparent;
        border: none;

        &:focus {
          border: none;
        }
      }
    }
  }
</style>
