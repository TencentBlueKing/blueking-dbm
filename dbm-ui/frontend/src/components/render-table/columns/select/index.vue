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
    class="table-edit-select"
    :class="{
      'is-error': Boolean(errorMessage),
      'is-disable': disabled,
    }"
    :style="{ height: rootHeight + 'px' }">
    <div
      v-if="errorMessage"
      class="select-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <BkSelect
      ref="selectRef"
      v-model="localValue"
      auto-focus
      v-bind="attrs"
      class="select-box"
      clearable
      :disabled="disabled"
      :input-search="false"
      @change="handleSelect"
      @clear="handleRemove">
      <template
        v-if="slots.trigger"
        #trigger>
        <slot name="trigger" />
      </template>
      <BkOption
        v-for="(item, index) in list"
        :key="index"
        :label="item.label"
        :value="item.value"
        @click="handleOptionClick(item.value)">
        <slot
          v-if="slots.default"
          :index="index"
          :option-item="item" />
        <span v-else>{{ item.label }}</span>
      </BkOption>
    </BkSelect>
  </div>
</template>
<script lang="ts">
  type IKey = string | number | string[];

  export interface IListItem {
    value: IKey;
    label: string;
    [x: string]: any;
  }
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { useAttrs } from 'vue';

  import { useResizeObserver } from '@vueuse/core';

  import useValidtor, { type Rules } from '../../hooks/useValidtor';

  interface Props {
    list: Array<IListItem>;
    rules?: Rules;
    disabled?: boolean;
    validateAfterSelect?: boolean; // 选择完立即校验
  }
  interface Emits {
    (e: 'change', value: IKey): void;
    (e: 'option-click', value: IKey): void;
  }

  interface Exposes {
    getValue: () => Promise<IKey>;
    hidePopover: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    rules: () => [],
    disabled: false,
    validateAfterSelect: true,
  });
  const emits = defineEmits<Emits>();

  const attrs = useAttrs();
  const modelValue = defineModel<IKey>();

  const slots = defineSlots<
    Partial<{
      default: (values: { optionItem: IListItem; index: number }) => VNode | VNode[];
      trigger: () => VNode | VNode[];
    }>
  >();

  const rootRef = ref();
  const localValue = ref<IKey>('');
  const rootHeight = ref(42);
  const selectRef = ref();

  const { message: errorMessage, validator } = useValidtor(props.rules);

  watch(
    modelValue,
    (value) => {
      if (value === undefined) {
        return;
      }
      localValue.value = value;
      if (typeof value !== 'object' && value) {
        if (!props.validateAfterSelect) {
          return;
        }

        validator(value);
        return;
      }
      if (Array.isArray(value) && value.length > 0) {
        validator(value);
        return;
      }
    },
    {
      immediate: true,
    },
  );

  // 选择
  const handleSelect = (value: IKey) => {
    localValue.value = value;
    if (!props.validateAfterSelect) {
      window.changeConfirm = true;
      modelValue.value = value;
      emits('change', localValue.value);
      return;
    }

    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      modelValue.value = value;
      emits('change', localValue.value);
    });
  };

  // 删除值
  const handleRemove = () => {
    localValue.value = '';
    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      modelValue.value = localValue.value;
      emits('change', localValue.value);
    });
  };

  const checkRootHeight = () => {
    if (!rootRef.value) {
      return;
    }

    rootHeight.value = rootRef.value.parentNode.clientHeight;
  };

  const handleOptionClick = (value: IKey) => {
    emits('option-click', value);
  };

  useResizeObserver(rootRef, _.throttle(checkRootHeight, 500));

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(() => localValue.value);
    },
    hidePopover() {
      selectRef.value.hidePopover();
    },
  });
</script>
<style lang="less" scoped>
  .is-error {
    background-color: #fff0f1 !important;

    :deep(input) {
      background-color: #fff0f1 !important;
    }

    :deep(.angle-up) {
      display: none !important;
    }

    :deep(.angle-down) {
      display: none !important;
    }
  }

  .is-disable {
    background-color: #fafbfd;
  }

  .table-edit-select {
    position: relative;
    overflow: hidden;
    color: #63656e;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.15s;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

    :deep(.select-box) {
      width: 100%;
      height: 100%;
      padding: 0;
      background: transparent;
      border: none;
      outline: none;

      .bk-select-trigger {
        height: 100%;
        background: inherit;

        .bk-input {
          height: 100%;
          border: none;
          outline: none;

          input {
            margin-left: 8px;
            background: transparent;
          }
        }
      }
    }

    .select-error {
      position: absolute;
      top: 0;
      right: 4px;
      bottom: 0;
      z-index: 99;
      display: flex;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }
</style>
