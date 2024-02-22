<template>
  <div class="search-input">
    <BkInput
      v-model="modelValue"
      autosize
      class="search-input-textarea"
      clearable
      :resize="false"
      type="textarea"
      @blur="handleBlur"
      @enter="handleEnter"
      @focus="handleFocus" />
    <div class="icon-area">
      <DbIcon
        v-if="modelValue"
        class="search-input-icon icon-close"
        type="close-circle-shape"
        @click="handleClose" />
      <DbIcon
        class="search-input-icon ml-4"
        type="search"
        @click="handleSearch" />
    </div>
  </div>
</template>

<script setup lang="ts">
  interface Emits {
    (e: 'search', value: string): void
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    default: '',
  });

  const handleEnter = (value: string, event: KeyboardEvent) => {
    // shift + enter 时，悬浮撑高
    // 只按下 enter 时，进行搜索
    if (!event.shiftKey) {
      event.preventDefault();
      emits('search', value);
    }
  };

  const handleFocus = () => {
    modelValue.value = modelValue.value.replace(/，/g, '\n');
  };

  const handleBlur = () => {
    modelValue.value = modelValue.value.replace(/\n/g, '，');
  };

  const handleClose = () => {
    modelValue.value = '';
  };

  const handleSearch = () => {
    emits('search', modelValue.value);
  };
</script>

<style lang="less" scoped>
  .search-input {
    position: relative;
    width: 900px;
    height: 40px;

    .search-input-textarea {
      position: absolute;
      z-index: 4;

      :deep(textarea) {
        max-height: 400px;
        min-height: 40px !important;
        padding: 12px 10px;
      }
    }

    .icon-area {
      position: absolute;
      top: 10px;
      right: 10px;
      z-index: 4;

      .search-input-icon {
        cursor: pointer;
      }

      .icon-close {
        color: #c4c6cc;
      }
    }
  }
</style>
