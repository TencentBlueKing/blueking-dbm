<template>
  <div
    v-bk-loading="{ isLoading: isPreChecking }"
    class="ticket-self-todo-page">
    <div class="header-action-box">
      <BkRadioGroup
        v-model="ticketStatus"
        type="capsule">
        <BkRadioButton
          v-for="item in statusList"
          :key="item.id"
          :label="item.id">
          {{ item.name }}
        </BkRadioButton>
      </BkRadioGroup>
      <BatchOperation
        v-model:is-show="isShowBatchOperation"
        class="w-88 ml-8"
        :ticket-list="selectTicketIdList"
        :ticket-status="ticketStatus" />
      <BkDatePicker
        v-model="datePickerValue"
        format="yyyy-MM-dd HH:mm:ss"
        :shortcuts="shortcutsRange"
        style="margin-left: auto"
        type="datetimerange"
        use-shortcut-text />
      <DbSearchSelect
        v-model="searachSelectValue"
        :data="searchSelectData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 450px; margin-left: 16px"
        unique-select />
    </div>
    <TicketTable
      ref="dataTable"
      :data-source="dataSource"
      :selectable="isSelectable"
      @selection="handleSelection">
      <template #action>
        <BkTableColumn
          fixed="right"
          :label="t('操作')"
          width="160">
          <template #default="{ data }: { data: TicketModel }">
            <RowAction
              v-if="data"
              :key="data.id"
              :data="data"
              :ticket-status="ticketStatus" />
          </template>
        </BkTableColumn>
      </template>
    </TicketTable>
    <AssistTab v-model="isAssist" />
  </div>
</template>
<script setup lang="ts">
  import { ref, shallowRef, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useDetailPreCheck from '@views/ticket-center/common/hooks/use-detail-precheck';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TicketTable from '@views/ticket-center/common/ticket-table/Index.vue';

  import AssistTab from './components/AssistTab.vue';
  import BatchOperation from './components/batch-operation/Index.vue';
  import RowAction from './components/row-action/Index.vue';
  import useStatusList from './hooks/useStatusList';

  const route = useRoute();
  const router = useRouter();

  const { t } = useI18n();

  const { defaultStatus: ticketStatus, list: statusList } = useStatusList();

  const { shortcutsRange, value: datePickerValue } = useDatePicker();

  const { searchSelectData, value: searachSelectValue } = useSearchSelect({
    exclude: ['status'],
  });

  const isPreChecking = useDetailPreCheck({
    id: Number(route.params.ticketId),
  });

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      is_assist: Boolean(Number(route.params.assist)),
      status: ticketStatus.value,
      todo: 'running',
    });

  const dataTableRef = useTemplateRef('dataTable');
  const selectTicketIdList = shallowRef<TicketModel[]>([]);
  const isShowBatchOperation = ref(false);
  const isAssist = ref(Number(route.params.assist));

  const isSelectable = computed(() =>
    [TicketModel.STATUS_APPROVE, TicketModel.STATUS_RESOURCE_REPLENISH, TicketModel.STATUS_TODO].includes(
      ticketStatus.value,
    ),
  );

  watch(ticketStatus, () => {
    dataTableRef.value!.fetchData();
    dataTableRef.value!.resetSelection();
    router.replace({
      params: {
        status: ticketStatus.value,
      },
    });
  });

  const handleSelection = (data: TicketModel[]) => {
    selectTicketIdList.value = data;
  };
</script>
<style lang="less">
  .ticket-self-todo-page {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
