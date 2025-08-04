<template>
  <div class="spec-detail-popover-info-item">
    <div class="label">{{ label }}:</div>
    <div class="value">
      <slot />
    </div>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    label: string;
  }

  defineProps<Props>();
</script>
<style lang="less">
  .spec-detail-popover-info-item {
    display: flex;
    overflow: hidden;
    font-size: 12px;
    line-height: 20px;
    color: #313238;
    flex: 1 1 100%;

    .label {
      height: 32px;
      padding-top: 6px;
      padding-right: 8px;
      color: #63656e;
      text-align: right;
      flex-shrink: 0;
    }

    .value {
      // width: 100%;
      padding-top: 6px;
      color: #313238;
    }
  }
</style>
