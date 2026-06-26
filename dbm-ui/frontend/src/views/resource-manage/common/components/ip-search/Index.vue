<template>
  <div
    ref="rootRef"
    class="host-import-ip-search"
    :class="{
      'is-focused': isFocused,
    }">
    <div
      class="host-import-ip-search-wrapper"
      @click="handleFocus">
      <div
        class="host-import-ip-search-tag-box"
        :class="{ 'host-import-ip-search-tag-box-display-value': isDisplayValueShow }">
        <div
          ref="root"
          class="host-import-ip-search-create-area"
          :class="{
            'is-focused': isFocused,
          }">
          <div
            v-if="isDisplayValueShow"
            class="create-area-name">
            {{ displayValue }}
          </div>
          <div
            v-else
            class="edit-area-input">
            <div
              :style="{
                'min-height': '22px',
                visibility: 'hidden',
                'white-space': 'pre-wrap',
                'word-break': 'break-all',
              }">
              {{ modelValue }}{{ modelValue.endsWith('\n') ? '\u200B' : '' }}
            </div>
            <textarea
              ref="textarea"
              v-model="modelValue"
              name="search"
              :placeholder="t('请输入 IP 地址，逗号 / 空格 / 换行分隔，Shift+Enter 换行，Enter 搜索')"
              spellcheck="false"
              @keydown="handleKeydown"
              @keyup="handleKeyup" />
          </div>
        </div>
      </div>
      <div
        v-if="modelValue"
        class="host-import-ip-search-clear-btn"
        @click="handleClear">
        <Icon name="close-circle-filled" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { Icon } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex } from '@common/regex';

  import useOutSideClick from './useOutSideClick';

  interface Emits {
    (e: 'search', value: string): void;
    (e: 'clear', value: string): void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  useOutSideClick(() => {
    if (!isFocused.value) {
      return;
    }
    isFocused.value = false;
    const parsedValue = parseMethod(modelValue.value);
    modelValue.value = parsedValue;

    // 失焦时触发搜索（仅当值确实发生了变化）
    if (parsedValue !== lastSearchedValue.value) {
      lastSearchedValue.value = parsedValue;
      emits('search', parsedValue);
    }
  });

  const textareaRef = useTemplateRef('textarea');
  const isFocused = ref(false);
  const lastSearchedValue = ref('');

  const isDisplayValueShow = computed(() => !isFocused.value && modelValue.value);
  const displayValue = computed(() => modelValue.value.replace(batchSplitRegex, ' | '));

  watch(isFocused, () => {
    nextTick(() => {
      if (isFocused.value) {
        textareaRef.value!.focus();
      }
    });
  });

  const parseMethod = (value: string) => {
    return _.uniq(_.filter(value.split(batchSplitRegex), (item) => Boolean(_.trim(item)))).join('\n');
  };

  const handleFocus = () => {
    isFocused.value = true;
  };

  const handleKeydown = (event: KeyboardEvent) => {
    // 手动输入模式支持 Shfit + Enter 换行
    if (['Enter', 'NumpadEnter'].includes(event.code) && event.shiftKey) {
      return true;
    }
    if (['Enter', 'NumpadEnter'].includes(event.code) && !event.isComposing) {
      event.preventDefault();
    }
  };

  const handleKeyup = (event: KeyboardEvent) => {
    setTimeout(() => {
      // 手动输入模式支持 Shfit + Enter 换行，默认换行行为
      if (['Enter', 'NumpadEnter'].includes(event.code) && event.shiftKey) {
        return true;
      }

      if (['Enter', 'NumpadEnter'].includes(event.code) && !event.isComposing) {
        event.preventDefault();
        // 没有输入任何值
        if (!modelValue.value) {
          lastSearchedValue.value = '';
          return;
        }

        // 如果允许输入多个需要解析分隔符
        modelValue.value = parseMethod(modelValue.value);

        lastSearchedValue.value = modelValue.value;
        isFocused.value = false;
        emits('search', modelValue.value);
      }
    });
  };

  // 处理粘贴
  // const handlePaste = () => {
  //   setTimeout(() => {
  //     modelValue.value = parseMethod(modelValue.value);
  //   });
  // };

  const handleClear = () => {
    modelValue.value = '';
    lastSearchedValue.value = '';
    emits('clear', '');
  };
</script>
<style lang="less">
  .host-import-ip-search {
    position: relative;
    z-index: 9;
    height: 32px;
    font-size: 12px;

    &.is-focused {
      .host-import-ip-search-wrapper {
        border-color: #1890ff;
      }

      .host-import-ip-search-tag-box {
        height: auto;
        flex-wrap: wrap;
      }
    }
  }

  .host-import-ip-search-wrapper {
    position: absolute;
    top: 0;
    right: 0;
    left: 0;
    color: #63656e;
    background: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
  }

  .host-import-ip-search-tag-box {
    display: flex;
    height: 30px;
    max-width: 100%;
    max-height: 400px;
    min-height: 30px;
    padding: 0 8px;
    padding-bottom: 4px;
    overflow: auto;
    box-sizing: border-box;
    transition: border 0.2s linear;
    align-items: flex-start;

    &.host-import-ip-search-tag-box-display-value {
      max-width: calc(100% - 24px);
      overflow: hidden;
    }
  }

  .host-import-ip-search-create-area {
    position: relative;
    display: inline-flex;
    max-width: 100%;
    min-width: 80px;
    min-height: 22px;
    margin-top: 4px;
    line-height: 22px;
    color: #63656e;
    flex: 1 0 auto;
    align-items: self-start;

    &.is-focused {
      flex: 0 0 100%;
    }

    .create-area-name {
      flex: 0 0 auto;
      padding-right: 4px;
      word-break: keep-all;
    }

    .edit-area-input {
      position: relative;
      min-height: 100%;
      flex: 1;
      overflow: hidden;

      textarea {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        padding: 0;
        overflow: hidden;
        font-size: inherit;
        line-height: inherit;
        color: inherit;
        white-space: pre-wrap;
        background: transparent;
        border: none;
        outline: none;
        resize: none;

        &::placeholder {
          color: #c4c6cc;
        }
      }
    }
  }

  .host-import-ip-search-clear-btn {
    position: absolute;
    top: 9px;
    right: 9px;
    display: flex;
    // width: 32px;
    // height: 32px;
    font-size: 14px;
    color: #c4c6cc;
    cursor: pointer;
    justify-content: center;
    align-items: center;

    &:hover {
      color: #979ba5;
    }
  }
</style>
