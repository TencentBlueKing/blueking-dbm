<template>
  <div
    v-if="abstractList.length"
    class="deliver-results-main">
    <div class="tip-display">
      {{ t('根据任务执行情况，输出以下任务执行结果摘要：') }}
    </div>
    <div class="table-list">
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
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTicketFlows } from '@services/source/ticketFlow';

  import TableCollapse from '@components/table-collapse/Index.vue';

  export type AbstractItem = {
    titles: {
      field: string;
      label: string;
    }[];
  } & Omit<ServiceReturnType<typeof getTicketFlows>[number]['output_data'][number], 'titles'>;

  interface Props {
    rootId: string;
    ticketId: number;
  }

  type Emits = (e: 'requestFinish', value: AbstractItem[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const abstractList = ref<AbstractItem[]>([]);

  const { run: fetchTicketFlows } = useRequest(getTicketFlows, {
    manual: true,
    onSuccess: (data) => {
      const currentFlow = data.find((item) => item.flow_obj_id === props.rootId);
      if (!currentFlow) {
        emits('requestFinish', []);
        return;
      }
      if (Array.isArray(currentFlow.output_data) && currentFlow.output_data.length) {
        abstractList.value = currentFlow.output_data
          .filter((item) => !item.hidden)
          .map((item) => ({
            ...item,
            titles: item.titles.map((item) => ({
              field: item.id,
              label: item.display_name,
            })),
          }));
      }
      emits('requestFinish', abstractList.value);
    },
  });

  watch(
    () => props.ticketId,
    () => {
      if (props.ticketId) {
        fetchTicketFlows({
          id: props.ticketId,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .deliver-results-main {
    padding: 0 24px;

    .tip-display {
      margin-bottom: 16px;
    }
  }

  .abstract-table-header-row {
    background-color: #fafbfd;
  }
</style>
