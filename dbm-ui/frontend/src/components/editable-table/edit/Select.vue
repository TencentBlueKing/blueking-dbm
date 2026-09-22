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
  <DbSelect
    v-model="modelValue"
    class="bk-editable-select"
    v-bind="{ ...attrs, ...props }"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus">
    <template
      v-if="slots.option"
      #optionRender="{ item }">
      <slot
        :item="item"
        name="option" />
    </template>
    <template v-if="slots.default">
      <slot />
    </template>
    <template
      v-if="slots.trigger"
      #trigger="{ selected }">
      <slot
        name="trigger"
        :selected="selected" />
    </template>
    <template
      v-if="slots.allOptionIcon"
      #allOptionIcon>
      <slot name="allOptionIcon" />
    </template>
    <template
      v-if="slots.tagRender"
      #tagRender="{ label, value }">
      <slot
        :label="label"
        name="tagRender"
        :value="value" />
    </template>
    <template
      v-if="slots.tag"
      #tag="{ selected }">
      <slot
        name="tag"
        :selected="selected" />
    </template>
  </DbSelect>
</template>
<script lang="ts">
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    clearable?: boolean;
    disabled?: boolean;
    filterable?: boolean;
    multiple?: boolean;
  }
</script>
<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import _ from 'lodash';
  import { useAttrs, type VNode, watch } from 'vue';

  import type { SelectedItem } from '@components/bkui-vue/select/common';

  import useColumn from '../useColumn';

  const props = defineProps<Props>();

  const emits = defineEmits<{
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }>();

  const slots = defineSlots<{
    allOptionIcon?: () => VNode;
    default?: () => VNode;
    option?: (value: { item: Record<string, any> }) => VNode;
    tag?: (value: { selected: SelectedItem[] }) => VNode;
    tagRender?: (item: SelectedItem) => VNode;
    trigger?: (value: { selected: SelectedItem[] }) => VNode;
  }>();

  const modelValue = defineModel<T>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  watch(modelValue, (newValue, oldValue) => {
    // 对于引用类型，实际值变化才校验
    if (!_.isEqual(newValue, oldValue)) {
      columnContext?.validate('change');
    }
  });

  const handleChange = (value: T) => {
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
</script>
<style lang="less">
  .bk-editable-table-body-column {
    // 边框统一由表格的 td::before 画，组件自身在默认态和聚焦态给触发器加的边框、投影都要抹掉
    .bk-editable-select {
      &.dbm-select {
        .dbm-select-input-box {
          height: 40px;
          background: transparent;
          border-color: transparent;
        }

        // 多选标签模式，标签换行时跟着把单元格撑高
        .dbm-select-tag {
          min-height: 40px;
          background: transparent;
          border-color: transparent;
        }

        &.is-focus {
          .dbm-select-input-box,
          .dbm-select-tag {
            border-color: transparent;
            box-shadow: none;
          }
        }
      }
    }

    &.is-readonly,
    &.is-disabled {
      .bk-editable-select {
        &.dbm-select {
          pointer-events: none;

          .dbm-select-clear-icon,
          .dbm-tag-close {
            display: none !important;
          }

          * {
            pointer-events: none;
          }
        }
      }
    }
  }
</style>
