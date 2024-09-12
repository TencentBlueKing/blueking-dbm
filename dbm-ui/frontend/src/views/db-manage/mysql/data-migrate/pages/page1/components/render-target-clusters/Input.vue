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
    class="table-edit-input"
    :class="{
      'is-focused': isFocused,
      'is-disabled': disabled,
      'is-readonly': readonly,
      'is-error': Boolean(errorMessage),
    }">
    <div
      ref="inputRef"
      class="inner-input"
      :class="{
        'is-error': Boolean(errorMessage),
        'is-single': !isFocused,
        'is-empty': isEmpty,
      }"
      contenteditable="true"
      :spellcheck="false"
      :style="inputStyles"
      @blur="handleBlur"
      @focus="handleFocus"
      @input="handleInput"
      @keydown="handleKeydown"
      @paste="handlePaste" />
    <div
      v-if="localValue && !isFocused && isOverflow"
      class="count-tag">
      <MiniTag :content="countText" />
    </div>
    <div
      v-if="!localValue"
      class="input-placeholder">
      {{ placeholder }}
    </div>
    <div
      v-if="errorMessage"
      class="input-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <BkPopover
      v-if="!isFocused"
      :content="t('选择集群')"
      placement="top"
      :popover-delay="0">
      <div
        class="edit-btn"
        @click="handleClickSeletor">
        <div class="edit-btn-inner">
          <DbIcon
            class="select-icon"
            type="host-select" />
        </div>
      </div>
    </BkPopover>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MiniTag from '@components/mini-tag/index.vue';
  import useValidtor, { type Rules } from '@components/render-table/hooks/useValidtor';

  import { encodeMult } from '@utils';

  import { useResizeObserver } from '@vueuse/core';

  interface Props {
    placeholder?: string;
    rules?: Rules;
    disabled?: boolean;
    readonly?: boolean;
  }

  interface Emits {
    (e: 'submit', value: string): void;
    (e: 'input', value: string): void;
    (e: 'click-seletor'): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
    focus: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '请输入',
    rules: undefined,
    multiInput: true,
    disabled: false,
    readonly: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const inputRef = ref();
  const isFocused = ref(false);
  const localValue = ref('');
  const isOverflow = ref(false);

  const countText = computed(() => t('共n个', [localValue.value.split(',').length]));
  const isEmpty = computed(() => !modelValue.value);
  const inputStyles = computed<any>(() => {
    if (isFocused.value) {
      return {};
    }
    return {
      height: '40px',
      overflow: 'hidden',
      'text-overflow': 'ellipsis',
      'white-space': 'nowrap',
    };
  });

  const { message: errorMessage, validator } = useValidtor(props.rules);

  watch(
    modelValue,
    (value) => {
      if (value) {
        setTimeout(() => {
          checkOverflow();
        });
      }
      nextTick(() => {
        if (localValue.value !== value) {
          localValue.value = value;
          inputRef.value.innerText = localValue.value;
          window.changeConfirm = true;
        }
      });
    },
    {
      immediate: true,
    },
  );

  const checkOverflow = () => {
    isOverflow.value = inputRef.value.clientWidth < inputRef.value.scrollWidth;
  };

  useResizeObserver(inputRef, checkOverflow);

  const handleClickSeletor = () => {
    emits('click-seletor');
  };

  // 获取焦点
  const handleFocus = () => {
    isFocused.value = true;
  };

  // 响应输入
  const handleInput = (event: Event) => {
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    nextTick(() => {
      const target = event.target as HTMLElement;
      localValue.value = _.trim(target.outerText);
      emits('input', localValue.value);
      window.changeConfirm = true;
      modelValue.value = localValue.value;
    });
  };

  // 失去焦点
  const handleBlur = (event: FocusEvent) => {
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    isFocused.value = false;
    checkOverflow();
    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      emits('submit', localValue.value);
    });
  };

  // enter键提交
  const handleKeydown = (event: KeyboardEvent) => {
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
      validator(localValue.value).then((result) => {
        if (result) {
          isFocused.value = false;
          window.changeConfirm = true;
          emits('submit', localValue.value);
        }
      });
    }
  };

  // 粘贴
  const handlePaste = (event: ClipboardEvent) => {
    let paste = (event.clipboardData || window.clipboardData).getData('text');
    paste = encodeMult(paste);

    const selection = window.getSelection();

    if (!selection || !selection.rangeCount) {
      return false;
    }
    selection.deleteFromDocument();
    selection.getRangeAt(0).insertNode(document.createTextNode(paste));
    localValue.value = paste;
    event.preventDefault();
    window.changeConfirm = true;
    modelValue.value = paste;
  };

  defineExpose<Exposes>({
    // 获取值
    getValue() {
      return validator(localValue.value).then(() => localValue.value);
    },
    // 编辑框获取焦点
    focus() {
      inputRef.value.focus();
      setTimeout(() => {
        inputRef.value.selectionStart = localValue.value.length;
        inputRef.value.selectionEnd = localValue.value.length;
      });
    },
  });
</script>
<style lang="less" scoped>
  .table-edit-input {
    position: relative;
    display: block;
    width: 100%;
    height: 42px;
    cursor: pointer;
    background: #fff;

    &:hover {
      .count-tag {
        display: none;
      }

      .edit-btn {
        z-index: 999;
      }
    }

    &.is-focused {
      z-index: 99;

      .inner-input {
        padding-right: 25px;
      }
    }

    &.is-disabled {
      cursor: not-allowed;

      .inner-input {
        pointer-events: none;
        background-color: #fafbfd;
      }
    }

    &.is-readonly {
      cursor: default;

      .inner-input {
        pointer-events: none;
      }

      .is-empty {
        pointer-events: none;
        background-color: #fafbfd;
      }
    }

    &.is-error {
      .inner-input {
        background-color: #fff1f1;
      }

      .edit-btn {
        right: 25px;
      }
    }

    .inner-input {
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
      max-height: 300px;
      min-height: 42px;
      padding: 10px 16px;
      overflow-y: auto;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
      word-break: break-all;
      background: inherit;
      border: 1px solid transparent;
      outline: none;
      box-sizing: border-box;

      &:hover {
        background-color: #fafbfd;
        border-color: #a3c5fd;
      }

      &:focus {
        border-color: #3a84ff;
      }

      &.is-single {
        & > * {
          display: inline;
        }

        br {
          white-space: nowrap;
          content: '\A';
        }
      }
    }

    .input-placeholder {
      position: absolute;
      top: 10px;
      right: 20px;
      left: 18px;
      z-index: 1;
      height: 20px;
      overflow: hidden;
      font-size: 12px;
      line-height: 20px;
      color: #c4c6cc;
      text-overflow: ellipsis;
      white-space: nowrap;
      pointer-events: none;
    }

    .input-error {
      position: absolute;
      right: 10px;
      top: -2px;
      z-index: 99;
      padding-bottom: 3px;
      font-size: 14px;
      color: #ea3636;
    }

    .count-tag {
      position: absolute;
      right: 16px;
      display: block;
    }

    .edit-btn {
      position: absolute;
      top: 0;
      right: 5px;
      z-index: -1;
      display: flex;
      width: 24px;
      height: 40px;
      align-items: center;

      .edit-btn-inner {
        display: flex;
        width: 24px;
        height: 24px;
        cursor: pointer;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        .select-icon {
          font-size: 16px;
          color: #979ba5;
        }

        &:hover {
          background: #f0f1f5;

          .select-icon {
            color: #3a84ff;
          }
        }
      }
    }

    .down-icon-main {
      position: absolute;
      top: 0;
      right: 0;
      display: flex;
      width: 30px;
      height: 40px;
      align-items: center;
      justify-content: center;

      .down-icon {
        font-size: 16px;
        background-color: #fff;
      }
    }
  }
</style>
