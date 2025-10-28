<template>
  <div class="db-ticket-info-item">
    <div class="db-ticket-info-item-label">{{ label }}：</div>
    <div class="db-ticket-info-item-value">
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
  // @label-width: 160px;

  .db-ticket-info-item {
    flex: 1 0 50%;
    display: flex;
    align-items: flex-start;
    min-height: 32px;
    line-height: 32px;
  }

  .db-ticket-info-item-label {
    // width: @label-width;
    padding-right: 8px;
    line-height: 32px;
    text-align: right;
    flex-shrink: 0;
  }

  .db-ticket-info-item-value {
    // width: calc(100% - @label-width);
    width: 100%;
    overflow: hidden;
    color: #313238;
    text-overflow: ellipsis;
    white-space: nowrap;

    & > .bk-table {
      margin-top: 8px;
    }
  }
</style>
