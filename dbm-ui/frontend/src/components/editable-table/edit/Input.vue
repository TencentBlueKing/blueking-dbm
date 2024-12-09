<template>
  <BkInput
    v-model="modelValue"
    class="bk-editable-input"
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
    &.bk-input {
      height: 40px;
      border: none;
      box-shadow: none !important;
    }

    .bk-input--text {
      background: transparent;
    }
  }
</style>
