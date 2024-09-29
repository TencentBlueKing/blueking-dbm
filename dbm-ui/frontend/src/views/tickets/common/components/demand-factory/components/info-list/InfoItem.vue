<template>
  <div class="db-ticket-info-item">
    <div class="db-ticket-info-item-lable">{{ label }}</div>
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
  .db-ticket-info-item {
    flex: 0 0 50%;
    display: flex;
    align-items: flex-start;
    min-height: 32px;
    line-height: 32px;
  }

  .db-ticket-info-item-lable {
    min-width: 140px;
    padding-right: 4px;
    line-height: 32px;
    text-align: right;
  }

  .db-ticket-info-item-value {
    overflow: hidden;
    color: #313238;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;

    & > .bk-vxe-table {
      margin-top: 8px;
    }
  }
</style>
