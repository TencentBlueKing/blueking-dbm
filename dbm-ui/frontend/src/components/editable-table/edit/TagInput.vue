<template>
  <BkTagInput
    v-model="modelValue"
    allow-create
    class="bk-editable-tag-input"
    clearable
    has-delete-icon
    @blur="handleBlur"
    @focus="handleFocus" />
</template>
<script setup lang="ts">
  import { watch } from 'vue';

  import useColumn from '../useColumn';

  const columnContext = useColumn();

  const modelValue = defineModel<string[]>();

  watch(modelValue, () => {
    columnContext?.validate();
  });

  const handleBlur = () => {
    columnContext?.blur();
  };

  const handleFocus = () => {
    columnContext?.focus();
  };
</script>
<style lang="less">
  .bk-editable-tag-input {
    &.bk-tag-input {
      width: 100%;

      .bk-tag-input-trigger {
        background: transparent;
        border: none;
        border-radius: 0;
      }
    }
  }
</style>
