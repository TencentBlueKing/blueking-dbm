<template>
  <BkSelect
    class="bk-editable-select"
    @blur="handleBlur"
    @focus="handleFocus">
    <slot />
  </BkSelect>
</template>
<script setup lang="ts">
  import useColumn from '../useColumn';

  const columnContext = useColumn();

  const handleBlur = () => {
    columnContext?.blur();
  };

  const handleFocus = () => {
    columnContext?.focus();
  };
</script>
<style lang="less">
  .bk-editable-select {
    width: 100%;

    .bk-input {
      height: 40px;
      border: none;
      box-shadow: none !important;
    }

    .bk-input--text {
      background: transparent;
    }
  }
</style>
