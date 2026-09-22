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
  <DbTagInput
    v-model="(modelValue as string[])"
    allow-create
    class="bk-editable-tag-input"
    clearable
    :collapse-tags="false"
    v-bind="attrs"
    :multiple="!single"
    :placeholder="placeholder"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus" />
</template>
<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import _ from 'lodash';
  import { watch } from 'vue';

  import useColumn from '../useColumn';

  export interface Props {
    placeholder?: string;
    single?: boolean;
  }

  export interface Emits<T> {
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }

  defineProps<Props>();
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
    // 边框统一由表格的 td::before 画，组件自身在默认 / hover / 聚焦三态给面板加的边框都要抹掉，否则会错开 1px 叠成双框
    .bk-editable-tag-input {
      &.db-tag-input {
        .db-tag-input-panel {
          min-height: 40px;
          background: transparent;
          border-color: transparent;
          border-radius: 0;
          align-items: center;
        }

        &:hover {
          .db-tag-input-panel {
            border-color: transparent;
          }
        }

        &.is-focus {
          .db-tag-input-panel {
            border-color: transparent;
          }
        }

        // 组件按 32px 行高定位清空按钮，这里行高是 40px，跟着首行标签重新居中
        .db-tag-input-clear {
          top: 20px;
        }
      }
    }

    &.is-readonly,
    &.is-disabled {
      .bk-editable-tag-input {
        &.db-tag-input {
          pointer-events: none;

          .db-tag-input-clear,
          .dbm-tag-close {
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
        &.db-tag-input {
          .db-tag-input-panel {
            background: #fff0f1;
          }
        }
      }
    }
  }
</style>
