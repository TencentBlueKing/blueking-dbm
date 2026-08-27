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
  <!-- prettier-ignore -->
  <BkTagInput
    v-model="(modelValue as string[])"
    allow-auto-match
    allow-create
    class="bk-editable-tag-input"
    clearable
    :copyable="false"
    has-delete-icon
    v-bind="{ ...attrs, ...props }"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus" />
</template>
<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import _ from 'lodash';
  import { watch } from 'vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  export interface Props {
    maxData?: number;
    placeholder?: string;
  }

  export interface Emits<T> {
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits<T>>();

  const modelValue = defineModel<T>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  watch(modelValue, (newValue, oldValue) => {
    // 对于引用类型，实际值变化才校验
    if (!_.isEqual(newValue, oldValue)) {
      columnContext?.validate('change');
    }
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

  const handleChange = () => {
    emits('change', modelValue.value as T);
  };
</script>
<style lang="less">
  .bk-editable-table-body-column {
    &.is-readonly,
    &.is-disabled {
      .bk-editable-tag-input {
        &.bk-tag-input {
          pointer-events: none;

          .clear-icon,
          .remove-tag {
            display: none !important;
          }

          * {
            pointer-events: none;
          }
        }
      }
    }

    &.is-error {
      .bk-editable-tag-input {
        .bk-tag-input {
          .bk-tag-input-trigger {
            background: #fff0f1;
          }
        }
      }
    }
  }

  .bk-editable-tag-input {
    &.bk-tag-input {
      width: 100%;

      .bk-tag-input-trigger {
        min-height: 40px;
        background: transparent;
        border: none;
        border-radius: 0;

        .placeholder {
          top: 50%;
          height: auto;
          transform: translateY(-50%);
        }

        .tag-input {
          background: transparent;
        }

        .tag-list {
          max-height: unset !important;
        }
      }
    }
  }
</style>
