<template>
  <div
    class="bk-quick-search-custom-input"
    :class="{ 'is-focused': isFocused }"
    @click="handleWrapperClick">
    <span class="bk-quick-search-custom-input-prefix">
      <SearchIcon />
    </span>
    <input
      ref="input"
      class="bk-quick-search-custom-input-inner"
      :placeholder="t('请输入关键字')"
      type="text"
      :value="modelValue"
      @blur="handleBlur"
      @focus="handleFocus"
      @input="handleInput"
      @keydown="handleKeyDown" />
    <span
      v-if="modelValue"
      class="bk-quick-search-custom-input-clear"
      @click.stop="handleClear">
      <CloseCircleFilledIcon />
    </span>
  </div>
</template>
<script setup lang="ts">
  import { CloseCircleFilledIcon, SearchIcon } from 'tdesign-icons-vue-next';
  import { onMounted, ref, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const inputRef = useTemplateRef('input');
  const isFocused = ref(false);

  const handleInput = (event: Event) => {
    const { value } = event.target as HTMLInputElement;
    modelValue.value = value;
  };

  const handleFocus = () => {
    isFocused.value = true;
  };

  const handleBlur = () => {
    isFocused.value = false;
  };

  const handleClear = () => {
    modelValue.value = '';
    inputRef.value?.focus();
  };

  const handleWrapperClick = () => {
    inputRef.value?.focus();
  };

  // 方向键交由外层菜单处理，避免移动输入框光标
  const handleKeyDown = (event: KeyboardEvent) => {
    const arrowKeys = ['ArrowUp', 'ArrowDown'];
    if (arrowKeys.includes(event.key)) {
      event.preventDefault();
    }
  };

  onMounted(() => {
    inputRef.value?.focus();
  });
</script>
<style lang="less">
  .bk-quick-search-custom-input {
    display: flex;
    width: 100%;
    height: 32px;
    padding: 0;
    font-size: 12px;
    line-height: normal;
    color: #63656e;
    cursor: text;
    background-color: #fff;
    border: none;
    border-bottom: 1px solid #eaebf0;
    transition: border-color 0.2s ease;
    align-items: center;

    &.is-focused {
      border-color: #3a84ff;
    }

    &-prefix {
      display: flex;
      margin-right: 6px;
      font-size: 14px;
      color: #979ba5;
      align-items: center;
    }

    &-inner {
      width: 100%;
      height: 100%;
      padding: 0;
      font-size: inherit;
      color: inherit;
      background: transparent;
      border: none;
      outline: none;
      flex: 1;

      &::placeholder {
        color: #c4c6cc;
      }
    }

    &-clear {
      display: flex;
      margin-left: 6px;
      font-size: 14px;
      color: #c4c6cc;
      cursor: pointer;
      align-items: center;

      &:hover {
        color: #979ba5;
      }
    }
  }
</style>
