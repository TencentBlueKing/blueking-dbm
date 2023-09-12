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
    class="table-edit-date-time"
    :class="{
      'is-error': Boolean(errorMessage),
      'is-disabled': disabled,
    }">
    <BkDatePicker
      append-to-body
      :clearable="false"
      :model-value="localValue"
      :placeholder="placeholder"
      style="width: 100%;"
      :type="type"
      v-bind="attrs"
      @change="handleChange"
      @open-change="handleOpenChange" />
    <div
      v-if="errorMessage"
      class="input-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    ref,
    useAttrs,
  } from 'vue';

  import useValidtor, {
    type Rules,
  } from './hooks/useValidtor';

  interface Props {
    modelValue?: [string, string] | string,
    placeholder?: string,
    rules?: Rules,
    type?: any,
    disabled?: boolean
  }

  interface Emits {
    (e: 'update:modelValue', value: Props['modelValue']): void;
    (e: 'change', value: any): void;
  }

  interface Exposes {
    getValue: () => Promise<Props['modelValue']>;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
    placeholder: '请选择',
    rules: undefined,
    type: undefined,
    disabled: false,
  });

  const emits = defineEmits<Emits>();

  const attrs = useAttrs();

  const localValue = ref(props.modelValue);

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);

  const handleChange = (value: Required<Props>['modelValue']) => {
    localValue.value = value;
    validator(localValue.value)
      .then(() => {
        window.changeConfirm = true;
        emits('update:modelValue', localValue.value);
        emits('change', localValue.value);
      });
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      validator(localValue.value);
    }
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value)
        .then(() => localValue.value);
    },
  });
</script>
<style lang="less">
  .table-edit-date-time {
    position: relative;

    &.is-error {
      .bk-date-picker {
        .bk-date-picker-editor {
          background-color: rgb(255 221 221 / 20%) !important;
        }
      }
    }

    &.is-disabled {
      pointer-events: none;

      .bk-date-picker {
        .bk-date-picker-editor {
          cursor: not-allowed;
          background-color: #fafbfd;
        }
      }
    }

    .bk-date-picker {
      .bk-date-picker-editor {
        height: 40px;
        line-height: 40px;
        border-color: transparent;
        border-radius: 0;

        &:hover {
          background-color: #fafbfd;
          border-color: #a3c5fd;
        }
      }

      .icon-wrapper {
        top: 4px;
      }
    }

    .input-error {
      position: absolute;
      top: 0;
      right: 0;
      bottom: 0;
      display: flex;
      padding-right: 10px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }
</style>
