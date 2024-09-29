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
  @label-width: 150px;

  .db-ticket-info-item {
    flex: 1 0 50%;
    display: flex;
    align-items: flex-start;
    min-height: 32px;
    line-height: 32px;
  }

  .db-ticket-info-item-lable {
    width: @label-width;
    padding-right: 8px;
    line-height: 32px;
    text-align: right;
  }

  .db-ticket-info-item-value {
    width: calc(100% - @label-width);
    overflow: hidden;
    color: #313238;
    text-overflow: ellipsis;
    white-space: nowrap;

    & > .bk-table {
      margin-top: 8px;
    }
  }
</style>
