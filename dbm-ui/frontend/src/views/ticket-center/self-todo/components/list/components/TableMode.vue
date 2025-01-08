<template>
  <div class="ticket-list-table-mode">
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
    <TableModeTable
      ref="dataTable"
      :data-source="dataSource"
      :row-class="rowClass"
      :selectable="isSelectable"
      @selection="handleSelection">
      <template #action>
        <BkTableColumn
          fixed="right"
          :label="t('操作')"
          width="220">
          <template #default="{ data }: { data: TicketModel }">
            <RowAction
              v-if="data"
              :key="data.id"
              :data="data"
              :ticket-status="ticketStatus"
              @go-ticket-detail="() => handleShowDetail(data)" />
          </template>
        </BkTableColumn>
      </template>
    </TableModeTable>
  </div>
</template>
<script setup lang="ts">
  import { onActivated, onDeactivated, ref, shallowRef, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import { useStretchLayout, useUrlSearch } from '@hooks';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TableModeTable from '@views/ticket-center/common/TableModeTable.vue';

  import BatchOperation from './components/batch-operation/Index.vue';
  import RowAction from './components/row-action/Index.vue';
  import useStatusList from './hooks/useStatusList';

  const route = useRoute();
  const router = useRouter();

  const { t } = useI18n();

  const { list: statusList, defaultStatus: ticketStatus } = useStatusList();

  const { removeSearchParam } = useUrlSearch();
  const { splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const { value: datePickerValue, shortcutsRange } = useDatePicker();

  const { value: searachSelectValue, searchSelectData } = useSearchSelect({
    exclude: ['status'],
  });

  const rowClass = (params: TicketModel) => (params.id === selectTicketId.value ? 'select-row' : '');

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      todo: 'running',
      self_manage: 1,
      status: ticketStatus.value,
      is_assist: Boolean(Number(route.params.assist)),
    });

  const dataTableRef = useTemplateRef('dataTable');
  const selectTicketIdList = shallowRef<TicketModel[]>([]);
  const isShowBatchOperation = ref(false);
  const selectTicketId = ref(0);

  const isSelectable = computed(() =>
    [TicketModel.STATUS_APPROVE, TicketModel.STATUS_RESOURCE_REPLENISH, TicketModel.STATUS_TODO].includes(
      ticketStatus.value,
    ),
  );

  const { pause: pauseTicketStatus, resume: resumeTicketStatus } = watch(ticketStatus, () => {
    dataTableRef.value!.fetchData();
    dataTableRef.value!.resetSelection();
    router.replace({
      params: {
        status: ticketStatus.value,
      },
    });
  });

  const handleShowDetail = (data: TicketModel) => {
    stretchLayoutSplitScreen();
    selectTicketId.value = data.id;
  };

  const handleSelection = (data: TicketModel[]) => {
    selectTicketIdList.value = data;
  };

  onActivated(() => {
    selectTicketId.value = Number(route.query.selectId);
    removeSearchParam('selectId');
    resumeTicketStatus();
  });

  onDeactivated(() => {
    pauseTicketStatus();
  });
</script>
<style lang="less">
  .ticket-list-table-mode {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }

    .select-row {
      td {
        background: #ebf2ff !important;
      }
    }
  }
</style>
