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
    class="table-edit-select-input"
    :class="{
      'is-focused': isFocused,
      'is-disabled': disabled,
      'is-readonly': readonly,
      'is-error': validateError,
      'is-seleced': !!localValue,
    }"
    @click="handleRootClick">
    <div
      ref="inputRef"
      class="inner-input"
      :class="{
        'is-error': validateError,
        'is-single': !isFocused,
        'is-empty': isEmpty,
      }"
      :contenteditable="!disabled"
      :spellcheck="false"
      :style="inputStyles"
      @blur="handleBlur"
      @focus="handleFocus"
      @input="handleInput"
      @keydown="handleKeydown"
      @paste="handlePaste" />
    <div
      v-if="!localValue"
      class="input-placeholder">
      {{ placeholder }}
    </div>
    <DbIcon
      v-if="localValue"
      class="remove-btn"
      :style="{ right: validateError ? '20px' : '4px' }"
      type="delete-fill"
      @click.self="handleRemove" />
    <DbIcon
      class="focused-flag"
      type="down-big" />
    <div
      v-if="validateError"
      class="input-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <div style="display: none">
      <div ref="popRef">
        <div
          v-if="inputSearch && (searchKey || renderList.length > 0)"
          class="search-input-box">
          <BkInput
            v-model="searchKey"
            behavior="simplicity"
            :placeholder="t('请输入字段名搜索')">
            <template #prefix>
              <span style="font-size: 14px; color: #979ba5">
                <DbIcon type="search" />
              </span>
            </template>
          </BkInput>
        </div>
        <div class="options-list">
          <div
            v-for="item in renderList"
            :key="item.id"
            v-bk-tooltips="{
              content: item.tooltips,
              placement: 'left',
              disabled: item.id === currentSelectItem?.id,
            }"
            class="option-item"
            :class="{
              active: item.id === currentSelectItem?.id,
            }"
            @click="handleSelect(item)">
            <template v-if="slots.option">
              <slot
                name="option"
                :option-item="item" />
            </template>
            <span v-else>{{ item.name }}</span>
          </div>
        </div>
        <div
          v-if="renderList.length < 1"
          style="color: #63656e; text-align: center">
          {{ t('数据为空') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';

  import { useDebouncedRef } from '@hooks';

  import { encodeMult, encodeRegexp } from '@utils';

  import useValidtor, { type Rules } from './hooks/useValidtor';

  import { t } from '@/locales';

  interface IListItem {
    id: string;
    name: string;
    tooltips?: string;
  }

  interface Props {
    list: Array<IListItem>;
    placeholder?: string;
    textarea?: boolean;
    rules?: Rules;
    disabled?: boolean;
    selectDisabled?: boolean;
    readonly?: boolean;
    inputSearch?: boolean;
    selectDisplayFun?: (value: string, item?: IListItem) => string;
  }

  interface Emits {
    (e: 'submit', value: string): void;
    (e: 'input', value: string): void;
    (e: 'overflow-change', value: boolean): void;
    (e: 'change', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
    getCurrentItem: () => IListItem | undefined;
    focus: () => void;
  }

  interface Slots {
    option(value: { optionItem: IListItem }): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: t('请输入'),
    textarea: false,
    rules: undefined,
    disabled: false,
    selectDisabled: false,
    readonly: false,
    inputSearch: true,
    selectDisplayFun: (value: string, item?: IListItem) => item?.name || '',
  });

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    default: '',
  });
  defineSlots<Slots>();

  let selectorInstance: Instance;

  const { error: validateError, message: errorMessage, validator } = useValidtor(props.rules);
  const searchKey = useDebouncedRef('');
  const slots = useSlots();

  const rootRef = ref<HTMLElement>();
  const popRef = ref<HTMLElement>();
  const inputRef = ref<HTMLElement>();
  const isFocused = ref(false);
  const isShowPop = ref(false);
  const isError = ref(false);
  const localValue = ref('');
  const currentSelectItem = ref<IListItem | undefined>();

  const isEmpty = computed(() => !modelValue.value);
  const inputStyles = computed(() => {
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

  const renderList = computed(() =>
    props.list.reduce((result, item) => {
      const reg = new RegExp(encodeRegexp(searchKey.value), 'i');
      if (reg.test(item.name)) {
        result.push(item);
      }
      return result;
    }, [] as Array<IListItem>),
  );

  watch(
    modelValue,
    (value) => {
      if (localValue.value !== value) {
        localValue.value = value;
        window.changeConfirm = true;
      }
      if (value) {
        setTimeout(() => {
          const isOverflow = inputRef.value!.clientWidth < inputRef.value!.scrollWidth;
          emits('overflow-change', isOverflow);
        });
      }
      validator(value);
    },
    {
      immediate: true,
    },
  );

  watch(
    localValue,
    () => {
      nextTick(() => {
        inputRef.value!.innerText = props.selectDisplayFun(localValue.value, currentSelectItem.value);
      });
    },
    {
      immediate: true,
    },
  );

  const handleRootClick = () => {
    if (props.disabled && props.selectDisabled) {
      return;
    }
    selectorInstance.show();
  };

  // 获取焦点
  const handleFocus = () => {
    isFocused.value = true;
  };

  const setCursorPosition = (el: Element, index: number) => {
    const range = document.createRange();
    const sel = window.getSelection();
    if (sel) {
      range.setStart(el.childNodes[0], index);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    }
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
    });
    setTimeout(() => {
      setCursorPosition(inputRef.value!, localValue.value.length);
    });
  };

  // 失去焦点
  const handleBlur = (event: FocusEvent) => {
    if (props.disabled) {
      event.preventDefault();
      return;
    }
    isFocused.value = false;
    if (!localValue.value) {
      return;
    }
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
      if (!props.textarea) {
        event.preventDefault();
        validator(localValue.value).then((result) => {
          if (result) {
            isFocused.value = false;
            window.changeConfirm = true;
            emits('submit', localValue.value);
          }
        });
        return;
      }
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
  };

  // 选择
  const handleSelect = (item: IListItem) => {
    if (currentSelectItem.value && item === currentSelectItem.value) {
      return;
    }
    localValue.value = item.id;
    currentSelectItem.value = item;
    selectorInstance.hide();
    modelValue.value = localValue.value;
    emits('change', localValue.value);
    window.changeConfirm = true;
  };

  // 删除值
  const handleRemove = () => {
    localValue.value = '';
    currentSelectItem.value = undefined;
    validator(localValue.value).then(() => {
      window.changeConfirm = true;
      modelValue.value = localValue.value;
      emits('change', localValue.value);
    });
  };

  onMounted(() => {
    if (modelValue.value) {
      const index = props.list.findIndex((listItem) => listItem.id === modelValue.value);
      if (index > -1) {
        const listItem = props.list[index];
        currentSelectItem.value = listItem;
      }
    }

    selectorInstance = tippy(rootRef.value as SingleTarget, {
      content: popRef.value,
      placement: 'bottom',
      appendTo: () => document.body,
      theme: 'table-edit-select-input light',
      maxWidth: 'none',
      trigger: 'manual',
      interactive: true,
      arrow: false,
      offset: [0, 8],
      onShow: () => {
        const { width } = rootRef.value!.getBoundingClientRect();
        Object.assign(popRef.value!.style, {
          width: `${width}px`,
        });
        isShowPop.value = true;
        isError.value = false;
      },
      onHide: () => {
        isShowPop.value = false;
        searchKey.value = '';
        validator(localValue.value);
      },
    });
  });

  onBeforeUnmount(() => {
    if (selectorInstance) {
      selectorInstance.hide();
      selectorInstance.unmount();
      selectorInstance.destroy();
    }
  });

  defineExpose<Exposes>({
    // 获取值
    getValue() {
      return validator(localValue.value).then(() => localValue.value);
    },
    getCurrentItem() {
      return currentSelectItem.value;
    },
    // 编辑框获取焦点
    focus() {
      inputRef.value!.focus();
    },
  });
</script>

<style lang="less" scoped>
  .table-edit-select-input {
    position: relative;
    display: flex;
    width: 100%;
    height: 42px;
    cursor: pointer;
    background: #fff;
    transition: all 0.15s;
    overflow: hidden;
    color: #63656e;
    border: 1px solid transparent;
    align-items: center;

    &:hover {
      background-color: #fafbfd;
      border-color: #a3c5fd;
    }

    &.is-focused {
      z-index: 99;
      border: 1px solid #3a84ff;
      .focused-flag {
        transform: rotateZ(-90deg);
      }
    }

    &.is-disabled {
      cursor: not-allowed;

      .inner-input {
        pointer-events: none;
        background-color: #fafbfd;
      }

      .remove-btn {
        display: none !important;
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
      background: rgb(255 221 221 / 20%);
      .inner-input {
        background-color: #fff1f1;
      }

      .focused-flag {
        display: none;
      }
    }

    &.is-seleced {
      &:hover {
        .remove-btn {
          display: block;
        }

        .focused-flag {
          display: none;
        }
      }
    }

    .inner-input {
      position: absolute;
      top: 0;
      right: 0;
      left: 0;
      max-height: 300px;
      min-height: 42px;
      padding: 0 16px;
      padding-top: 10px;
      overflow-y: auto;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
      word-break: break-all;
      background: inherit;
      outline: none;

      &:hover {
        background-color: #fafbfd;
        border-color: #a3c5fd;
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
      top: 0;
      right: 4px;
      bottom: 0;
      display: flex;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }

    .focused-flag {
      position: absolute;
      right: 4px;
      font-size: 14px;
      transition: all 0.15s;
    }

    .remove-btn {
      position: absolute;
      right: 4px;
      z-index: 1;
      display: none;
      font-size: 16px;
      color: #c4c6cc;
      transition: all 0.15s;

      &:hover {
        color: #979ba5;
      }
    }
  }
</style>

<style lang="less">
  .tippy-box[data-theme~='table-edit-select-input'] {
    .tippy-content {
      padding: 0;
      font-size: 12px;
      line-height: 32px;
      color: #26323d;
      background-color: #fff;
      border: 1px solid #dcdee5;
      border-radius: 2px;
      user-select: none;

      .search-input-box {
        padding: 0 12px;

        .bk-input--text {
          background-color: #fff;
        }
      }

      .options-list {
        max-height: 300px;
        // margin-top: 8px;
        overflow-y: auto;
      }

      .option-item {
        height: 32px;
        padding: 0 12px;
        overflow: hidden;
        line-height: 32px;
        text-overflow: ellipsis;
        white-space: pre;

        &:hover {
          color: #63656e;
          cursor: pointer;
          background-color: #f5f7fa;
        }

        &.active {
          color: #3a84ff;
          background-color: #e1ecff;
        }

        &.disabled {
          color: #c4c6cc;
          cursor: not-allowed;
          background-color: transparent;
        }
      }

      .option-item-value {
        padding-left: 8px;
        overflow: hidden;
        color: #979ba5;
        text-overflow: ellipsis;
        word-break: keep-all;
        white-space: nowrap;
      }
    }
  }
</style>
