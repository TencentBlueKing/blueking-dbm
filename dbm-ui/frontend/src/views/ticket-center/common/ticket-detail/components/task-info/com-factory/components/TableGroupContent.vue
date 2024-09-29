<template>
  <div class="table-group-content">
    <div
      v-for="(column, index) in columns"
      :key="index"
      class="content-item">
      <div class="item-title">{{ column.title }}：</div>
      <div class="item-content">
        <Component :is="column.render" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    columns: {
      title: string;
      render: () => VNode | string | number | null;
    }[];
  }

  defineProps<Props>();
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
        width: 72px;
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
