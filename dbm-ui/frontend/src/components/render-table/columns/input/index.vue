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
    class="table-edit-input"
    :class="{
      'is-error': Boolean(errorMessage),
      'is-disabled': disabled,
      'is-password': isPassword,
    }">
    <BkInput
      class="input-box"
      :disabled="disabled"
      :max="max"
      :min="min"
      :model-value="modelValue"
      :placeholder="placeholder"
      :type="type"
      @blur="handleBlur"
      @change="handleInput"
      @focus="() => (isBlur = false)"
      @input="handleInput"
      @keydown="handleKeydown"
      @paste="handlePaste">
      <template #suffix />
    </BkInput>
    <DbIcon
      v-if="errorMessage"
      v-bk-tooltips="errorMessage"
      class="error-icon"
      type="exclamation-fill" />
    <div
      v-if="isShowBlur && isBlur"
      class="blur-dispaly-main">
      <slot name="blur" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { encodeMult } from '@utils';

  import useValidtor, { type Rules } from '../../hooks/useValidtor';

  interface Props {
    placeholder?: string,
    rules?: Rules,
    disabled?: boolean,
    type?: string,
    min?: number,
    max?: number,
    isShowBlur?: boolean,
  }

  interface Emits {
    (e: 'submit', value: string): void,
  }

  interface Exposes {
    getValue: () => Promise<string>,
    focus: () => void,
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '请输入',
    rules: undefined,
    disabled: false,
    type: 'text',
    min: Number.MIN_SAFE_INTEGER,
    max: Number.MAX_SAFE_INTEGER,
    isShowBlur: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const rootRef = ref<HTMLElement>();
  const isBlur = ref(true);

  const isPassword = computed(() => props.type === 'password');

  let oldInputText = ''

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);

  watch(modelValue, (value) => {
    if (value) {
      window.changeConfirm = true;
    }
  });

  // 响应输入
  const handleInput = (value: string) => {
    isBlur.value = false;
    window.changeConfirm = true;
    modelValue.value = value;
  };

  // 失去焦点
  const handleBlur = (event: FocusEvent) => {
    isBlur.value = true;
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    if (modelValue.value) {
      if (oldInputText === modelValue.value) {
        return;
      }
      oldInputText = modelValue.value;
      validator(modelValue.value)
        .then(() => {
          window.changeConfirm = true;
          emits('submit', modelValue.value);
        });
      return;
    }
    emits('submit', modelValue.value);
  };

  // enter键提交
  const handleKeydown = (value: string, event: KeyboardEvent) => {
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    if (event.isComposing) {
      // 跳过输入法复合事件
      return;
    }
    if (event.which === 13 || event.key === 'Enter') {
      if (oldInputText === modelValue.value) {
        return;
      }
      oldInputText = modelValue.value;
      event.preventDefault();
      validator(modelValue.value)
        .then((result) => {
          if (result) {
            window.changeConfirm = true;
            emits('submit', modelValue.value);
          }
        });
    }
  };

  // 粘贴
  const handlePaste = (value: string, event: ClipboardEvent) => {
    event.preventDefault();
    let paste = (event.clipboardData || window.clipboardData).getData('text');
    paste = encodeMult(paste);
    modelValue.value = paste.replace(/^\s+|\s+$/g, '');
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(modelValue.value).then(() => modelValue.value);
    },
    focus() {
      (rootRef.value as HTMLElement).querySelector('input')?.focus();
    },
  });
</script>
<style lang="less" scoped>
  .is-error {
    :deep(input) {
      padding: 0 16px;
      background-color: #fff0f1;
      border: 1px solid transparent;
      border-radius: 0;

      &:hover {
        cursor: pointer;
        background-color: #fafbfd;
        border: 1px solid #a3c5fd;
      }

      &:focus {
        border-color: #3a84ff;
      }
    }

    :deep(.bk-input--number-control) {
      display: none !important;
    }

    :deep(.bk-input--suffix-icon) {
      display: none !important;
    }
  }

  .is-disabled {
    :deep(input) {
      cursor: not-allowed !important;
      border: none !important;
    }

    :deep(.bk-input--number-control) {
      background-color: #fafbfd;
    }
  }

  .is-password {
    :deep(.bk-input--text) {
      padding-right: 25px;
    }

    :deep(.bk-input--suffix-icon) {
      position: absolute;
      right: 1px;
      display: flex;
      height: 40px;
      justify-content: center;
      padding: 0 5px;
      background: transparent;
    }
  }

  .table-edit-input {
    position: relative;
    min-height: 42px;
    cursor: pointer;
    background: #fff;

    .input-box {
      width: 100%;
      height: 42px;
      padding: 0;
      background: inherit;
      border: none;
      outline: none;

      :deep(input) {
        padding-left: 16px;
        border: 1px solid transparent;
        border-radius: 0;

        &:hover {
          cursor: pointer;
          background-color: #fafbfd;
          border: 1px solid #a3c5fd;
        }

        &:focus {
          border-color: #3a84ff;
        }
      }

      :deep(.bk-input--number-control) {
        position: absolute;
        right: 1px;
        background: transparent;
      }
    }

    .error-icon {
      position: absolute;
      top: 14px;
      right: 10px;
      display: flex;
      font-size: 14px;
      color: #ea3636;
    }

    .blur-dispaly-main {
      padding: 0 16px;
    }
  }
</style>
