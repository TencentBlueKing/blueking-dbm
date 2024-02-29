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
      v-model="localValue"
      class="input-box"
      :disabled="disabled"
      :max="max"
      :min="min"
      :placeholder="placeholder"
      :type="type"
      @blur="handleBlur"
      @change="handleInput"
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
    max?: number
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
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const rootRef = ref<HTMLElement>();
  const localValue = ref('');

  const isPassword = computed(() => props.type === 'password');

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);

  watch(modelValue, (value) => {
    nextTick(() => {
      if (localValue.value !== value) {
        localValue.value = value;
        window.changeConfirm = true;
      }
    });
  }, {
    immediate: true,
  });

  // 响应输入
  const handleInput = (value: string) => {
    localValue.value = value;
    window.changeConfirm = true;
    modelValue.value = value;
  };

  // 失去焦点
  const handleBlur = (event: FocusEvent) => {
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    if (localValue.value) {
      validator(localValue.value)
        .then(() => {
          window.changeConfirm = true;
          emits('submit', localValue.value);
        });
      return;
    }
    emits('submit', localValue.value);
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
      event.preventDefault();
      validator(localValue.value)
        .then((result) => {
          if (result) {
            window.changeConfirm = true;
            emits('submit', localValue.value);
          }
        });
    }
  };

  // 粘贴
  const handlePaste = (value: string, event: ClipboardEvent) => {
    event.preventDefault();
    let paste = (event.clipboardData || window.clipboardData).getData('text');
    paste = encodeMult(paste);
    localValue.value = paste.replace(/^\s+|\s+$/g, '');
    window.changeConfirm = true;
    modelValue.value = localValue.value;
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value).then(() => localValue.value);
    },
    focus() {
      (rootRef.value as HTMLElement).querySelector('input')?.focus();
    },
  });
</script>
<style lang="less" scoped>
  .is-error {
    :deep(input) {
      background-color: #fff0f1;
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
    display: block;
    height: 42px;
    cursor: pointer;
    background: #fff;

    .input-box {
      width: 100%;
      height: 100%;
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
  }
</style>
