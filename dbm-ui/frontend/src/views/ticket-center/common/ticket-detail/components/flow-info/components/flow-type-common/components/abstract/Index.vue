<template>
  <FlowCollapse
    v-if="abstractList.length"
    :title="t('执行摘要')">
    <div class="flow-abstract-main">
      <TableCollapse
        v-for="(item, index) in abstractList"
        :key="index"
        :title="item.table_name">
        <BkTable
          :columns="item.titles"
          :data="item.values"
          header-row-class-name="abstract-table-header-row" />
      </TableCollapse>
    </div>
  </FlowCollapse>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import FlowCollapse from '../FlowCollapse.vue';

  import TableCollapse from './components/TableCollapse.vue';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

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
    display: flex;
    width: 100%;
    padding-left: 16px;
    background: #f5f7fa;
    flex-direction: column;
    gap: 16px;

    .item-main {
      width: 100%;

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

  .abstract-table-header-row {
    background-color: #fafbfd;
  }
</style>
