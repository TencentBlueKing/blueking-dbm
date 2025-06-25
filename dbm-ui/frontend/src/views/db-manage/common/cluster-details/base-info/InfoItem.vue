<template>
  <div class="cluster-detail-base-info-item">
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
  .cluster-detail-base-info-item {
    display: flex;
    overflow: hidden;
    font-size: 12px;
    line-height: 20px;
    color: #313238;
    flex: 1 1 50%;

    .label {
      height: 32px;
      padding-top: 6px;
      padding-right: 8px;
      color: #4d4f56;
      text-align: right;
      flex-shrink: 0;
    }

    .value {
      width: 100%;
      padding-top: 6px;
    }
  }
</style>
