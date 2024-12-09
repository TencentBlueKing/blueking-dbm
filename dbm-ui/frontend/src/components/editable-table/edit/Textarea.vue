<template>
  <BkInput
    v-model="modelValue"
    autosize
    class="bk-editable-input"
    :resize="false"
    type="textarea"
    @blur="handleBlur"
    @focus="handleFocus" />
</template>
<script setup lang="ts">
  import { watch } from 'vue';

  import useColumn from '../useColumn';

  const columnContext = useColumn();

  const modelValue = defineModel<string>();

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
  .bk-editable-input {
    &.bk-textarea {
      min-height: 40px;
      background: transparent;
      border: none;
      border-radius: none;
      box-shadow: none !important;

      textarea {
        background: transparent;
      }
    }
  }
</style>
