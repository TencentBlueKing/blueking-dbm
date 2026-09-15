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
  <BkSelect
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
  </BkSelect>
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

  import useColumn from '../useColumn';

  type ISelected = {
    label: string;
    value: number | string;
  };

  const props = defineProps<Props>();

  const emits = defineEmits<{
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }>();

  const slots = defineSlots<{
    allOptionIcon?: () => VNode;
    default?: () => VNode;
    option?: (value: { item: Record<string, any> }) => VNode;
    tag?: (value: { selected: ISelected[] }) => VNode;
    tagRender?: (item: ISelected) => VNode;
    trigger?: (value: { selected: ISelected[] }) => VNode;
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
    &.is-readonly,
    &.is-disabled {
      .bk-editable-select {
        &.bk-select {
          pointer-events: none;

          .bk-tag-close,
          .clear-icon {
            display: none !important;
          }

          * {
            pointer-events: none;
          }
        }
      }
    }
  }

  .bk-editable-select {
    &.bk-select {
      width: 100%;

      .bk-input {
        height: 40px;
        border: none;
        box-shadow: none !important;
      }

      .bk-input--text {
        background: transparent;
      }

      .bk-select-trigger {
        display: flex;
        align-items: center;
        height: 40px !important;

        .bk-select-tag {
          height: 40px !important;
          background: transparent;
          border: none !important;
          box-shadow: none !important;
          flex: 1;
        }
      }
    }
  }
</style>
