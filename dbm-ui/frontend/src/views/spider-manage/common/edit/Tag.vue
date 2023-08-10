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
    class="table-edit-tag"
    :class="{['is-error']: Boolean(errorMessage),}">
    <BkTagInput
      v-model="localValue"
      allow-create
      :clearable="false"
      has-delete-icon
      :placeholder="placeholder"
      @change="handleChange" />
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
  } from 'vue';

  import useValidtor, {
    type Rules,
  } from './hooks/useValidtor';

  interface Props {
    modelValue?: Array<string>,
    placeholder?: string,
    rules?: Rules,
  }

  interface Emits {
    (e: 'update:modelValue', value: string []): void;
    (e: 'change', value: string []): void;
  }

  interface Exposes {
    getValue: () => Promise<string []>;
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: () => [],
    placeholder: '请输入',
    rules: undefined,
  });

  const emits = defineEmits<Emits>();

  const localValue = ref(props.modelValue);

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);

  const handleChange = (value: string[]) => {
    localValue.value = value;
    validator(localValue.value)
      .then(() => {
        window.changeConfirm = true;
        emits('update:modelValue', localValue.value);
        emits('change', localValue.value);
      });
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value)
        .then(() => localValue.value);
    },
  });
</script>
<style lang="less">
  .table-edit-tag {
    position: relative;

    &.is-error {
      .bk-tag-input {
        .bk-tag-input-trigger {
          background: rgb(255 221 221 / 20%);

          .placeholder {
            line-height: 40px;
          }
        }
      }
    }

    .bk-tag-input {
      .bk-tag-input-trigger {
        min-height: 40px;
        border-color: transparent;
        border-radius: 0;

        &:hover {
          background-color: #fafbfd;
          border-color: #a3c5fd;
        }

        &.active {
          border-color: #3a84ff;
        }

        .tag-input {
          background-color: transparent !important;
        }

        .placeholder {
          top: 0;
          height: 40px;
          line-height: 40px;
        }
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
