<template>
  <div class="table-group-content">
    <div
      v-for="(column, index) in columns"
      :key="index"
      class="content-item">
      <div
        class="item-title"
        :style="{ width: `${titleWidth}px` }">
        {{ column.title }}：
      </div>
      <div class="item-content">
        <Component :is="column.render" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { VNode } from 'vue';

  interface Props {
    columns: {
      render: () => VNode | string | number | null;
      title: string;
    }[];
    titleWidth?: number;
  }

  withDefaults(defineProps<Props>(), {
    titleWidth: 72,
  });
</script>

<style lang="less" scoped>
  .table-group-content {
    display: flex;
    flex-direction: column;

    .content-item {
      display: flex;
      align-items: center;
      width: 100%;
      line-height: 20px;

      .item-title {
        // width: 72px;
        text-align: right;
      }

      .item-content {
        flex: 1;
        display: flex;
        align-items: center;
        overflow: hidden;
      }
    }
  }
</style>
