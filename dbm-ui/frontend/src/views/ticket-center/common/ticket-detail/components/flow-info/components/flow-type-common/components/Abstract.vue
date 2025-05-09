<template>
  <div
    v-if="abstractList.length"
    class="flow-abstract-main">
    <div
      v-for="(item, index) in abstractList"
      :key="index"
      class="item-main">
      <div class="title-main">{{ item.table_name }}</div>
      <div class="table-main">
        <BkTable
          border="outer"
          :columns="item.titles"
          :data="item.values" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  const props = defineProps<Props>();

  const abstractList = computed(() => {
    if (!props.data.output_data.length) {
      return [];
    }

    return props.data.output_data
      .filter((item) => !item.hidden)
      .map((item) => {
        return {
          ...item,
          titles: item.titles.map((item) => ({
            field: item.id,
            label: item.display_name,
          })),
        };
      });
  });
</script>
<style lang="less">
  .flow-abstract-main {
    width: 100%;
    padding: 0 16px 16px;
    margin: 12px 0;
    background-color: #fbfbfb;

    .item-main {
      width: 100%;
      padding-top: 16px;

      .title-main {
        font-size: 14px;
        font-weight: 700;
        color: #313238;
      }

      .table-main {
        padding: 12px 10px 0;
      }
    }
  }
</style>
