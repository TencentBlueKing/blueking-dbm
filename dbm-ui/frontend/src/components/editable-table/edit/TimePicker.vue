<template>
  <BkTimePicker
    append-to-body
    class="bk-editable-time-picker"
    @blur="handleBlur"
    @focus="handleFocus" />
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
  .bk-editable-time-picker {
    &.bk-date-picker {
      width: 100%;

      .icon-wrapper {
        height: 40px;
      }

      .bk-date-picker-editor {
        height: 40px;
        background: transparent;
        border: none;
      }
    }
  }
</style>
