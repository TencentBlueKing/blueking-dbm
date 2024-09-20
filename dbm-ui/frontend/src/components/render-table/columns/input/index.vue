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
      ref="inputRef"
      class="input-box"
      :disabled="disabled"
      :max="max"
      :min="min"
      :model-value="modelValue"
      :placeholder="placeholder"
      :type="type"
      v-bind="$attrs"
      @blur="handleBlur"
      @change="handleInput"
      @focus="handleFocus"
      @input="handleInput"
      @keydown="handleKeydown"
      @paste="handlePaste">
    </BkInput>
    <div class="suspend-main">
      <DbIcon
        v-if="clearable && modelValue"
        class="clear-icon"
        type="close-circle-shape"
        @click="handleClear" />
      <slot name="suspend" />
      <DbIcon
        v-if="errorMessage"
        v-bk-tooltips="errorMessage"
        class="error-icon"
        type="exclamation-fill" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { encodeMult } from '@utils';

  import useValidtor, { type Rules } from '../../hooks/useValidtor';

  interface Props {
    placeholder?: string;
    rules?: Rules;
    disabled?: boolean;
    type?: string;
    min?: number;
    max?: number;
    clearable?: boolean;
    ignoreSameInput?: boolean;
    pasteFn?: (value: string) => string;
  }

  interface Emits {
    (e: 'blur', value: string): void;
    (e: 'input', value: string): void;
    (e: 'submit', value: string): void;
    (e: 'error', result: boolean): void;
    (e: 'focus'): void;
    (e: 'clear'): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
    validator: () => Promise<boolean>;
    focus: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '请输入',
    rules: undefined,
    disabled: false,
    type: 'text',
    min: Number.MIN_SAFE_INTEGER,
    max: Number.MAX_SAFE_INTEGER,
    clearable: true,
    ignoreSameInput: false,
    pasteFn: undefined,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: '',
  });

  defineSlots<{
    suspend: any;
    default: any;
  }>();

  const rootRef = ref<HTMLElement>();

  const isPassword = computed(() => props.type === 'password');

  let oldInputText = '';

  const { message: errorMessage, validator } = useValidtor(props.rules);

  watch(
    modelValue,
    (value) => {
      if (value) {
        window.changeConfirm = true;
      }
    },
    {
      immediate: true,
    },
  );

  // 响应输入
  const handleInput = (value: string) => {
    window.changeConfirm = true;
    modelValue.value = value;
    emits('input', value);
  };

  const handleFocus = () => {
    emits('focus');
  };

  const handleClear = () => {
    modelValue.value = '';
    validator('')
      .catch(() => emits('error', true))
      .finally(() => {
        emits('clear');
      });
  };

  // 失去焦点
  const handleBlur = (event: FocusEvent) => {
    setTimeout(() => {
      emits('blur', modelValue.value);
      if (props.disabled) {
        event.preventDefault();
        return;
      }
      if (modelValue.value) {
        if (oldInputText === modelValue.value && props.ignoreSameInput) {
          return;
        }
        oldInputText = modelValue.value;
        validator(modelValue.value)
          .then(() => {
            window.changeConfirm = true;
            emits('error', false);
            emits('submit', modelValue.value);
          })
          .catch(() => emits('error', true));
        return;
      }
      emits('submit', modelValue.value);
    }, 100);
  };

  // enter键提交
  const handleKeydown = (value: string, event: KeyboardEvent) => {
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    if (event.isComposing || props.type === 'textarea') {
      // 跳过输入法复合事件
      return;
    }
    if (event.which === 13 || event.key === 'Enter') {
      if (oldInputText === modelValue.value && props.ignoreSameInput) {
        return;
      }
      oldInputText = modelValue.value;
      event.preventDefault();
      validator(modelValue.value)
        .then((result) => {
          if (result) {
            window.changeConfirm = true;
            emits('error', false);
            emits('submit', modelValue.value);
          }
        })
        .catch(() => emits('error', true));
    }
  };

  // 粘贴
  const handlePaste = (value: string, event: any) => {
    event.preventDefault();
    // 获取光标位置
    const cursorPosition = event.target.selectionStart;
    let paste = (event.clipboardData || window.clipboardData).getData('text');
    paste = encodeMult(paste);
    paste = paste.replace(/^\s+|\s+$/g, '');
    paste = props.pasteFn ? props.pasteFn(paste) : paste;
    modelValue.value = modelValue.value.slice(0, cursorPosition) + paste + modelValue.value.slice(cursorPosition);
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(modelValue.value)
        .then(() => modelValue.value)
        .catch(() => Promise.reject(modelValue.value));
    },
    validator() {
      return validator(modelValue.value).then(
        () => true,
        () => false,
      );
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

    :deep(textarea) {
      background-color: #fff0f1 !important;

      &:hover {
        cursor: pointer;
        background-color: #fafbfd;
        border: 1px solid #a3c5fd;
      }

      &:focus {
        border-color: #3a84ff;
      }

      textarea {
        background-color: #fff0f1;
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

    &:hover {
      .clear-icon {
        display: block !important;
      }
    }

    .input-box {
      width: 100%;
      min-height: 42px;
      padding: 0;
      background: inherit;
      border: none;
      outline: none;

      :deep(textarea) {
        min-height: 42px !important;
        line-height: 2.5 !important;
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

    .suspend-main {
      position: absolute;
      top: 50%;
      right: 10px;
      display: flex;
      font-size: 14px;
      transform: translateY(-50%);
      align-items: center;
      gap: 8px;

      .clear-icon {
        display: none;
        color: #c4c6cc;

        &:hover {
          color: #979ba5;
        }
      }

      .error-icon {
        color: #ea3636;
      }
    }
  }
</style>
