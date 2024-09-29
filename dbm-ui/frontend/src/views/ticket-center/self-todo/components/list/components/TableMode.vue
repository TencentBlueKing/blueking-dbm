<template>
  <div class="ticket-list-table-mode">
    <div class="header-action-box">
      <BkRadioGroup
        v-model="ticketStatus"
        type="capsule">
        <BkRadioButton :label="TicketModel.STATUS_TODO">
          {{ t('待我审批') }}
          <span>({{ ticketCount?.TODO }})</span>
        </BkRadioButton>
        <BkRadioButton :label="TicketModel.STATUS_APPROVE">
          {{ t('待我确认') }}
          <span>({{ ticketCount?.APPROVE }})</span>
        </BkRadioButton>
        <BkRadioButton :label="TicketModel.STATUS_RESOURCE_REPLENISH">
          {{ t('待我补货') }}
          <span>({{ ticketCount?.RESOURCE_REPLENISH }})</span>
        </BkRadioButton>
        <BkRadioButton :label="TicketModel.STATUS_FAILED">
          {{ t('待我处理失败') }}
          <span>({{ ticketCount?.FAILED }})</span>
        </BkRadioButton>
        <BkRadioButton :label="TicketModel.STATUS_RUNNING">
          {{ t('待我继续') }}
          <span>({{ ticketCount?.RUNNING }})</span>
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
      selectable
      @selection="handleSelection">
      <template #prepend>
        <BkTableColumn
          field="id"
          fixed="left"
          :label="t('单据')"
          width="100">
          <template #default="{ data }: { data: IRowData }">
            <BkButton
              v-if="data"
              text
              theme="primary"
              @click="() => handleShowDetail(data)">
              {{ data.id }}
            </BkButton>
          </template>
        </BkTableColumn>
      </template>
      <template #action>
        <BkTableColumn
          fixed="right"
          :label="t('操作')"
          width="250">
          <template #default="{ data }: { data: IRowData }">
            <RowAction
              v-if="data"
              :data="data"
              :ticket-status="ticketStatus" />
          </template>
        </BkTableColumn>
      </template>
    </TableModeTable>
  </div>
</template>
<script setup lang="ts">
  import { onMounted, ref, shallowRef, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import { useStretchLayout, useTicketCount, useUrlSearch } from '@hooks';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TableModeTable from '@views/ticket-center/common/TableModeTable.vue';

  import BatchOperation from './components/BatchOperation.vue';
  import RowAction from './components/row-action/Index.vue';

  type IRowData = TicketModel<unknown>;

  const route = useRoute();
  const router = useRouter();

  const { t } = useI18n();
  const { data: ticketCount } = useTicketCount();
  const { appendSearchParams, getSearchParams } = useUrlSearch();

  const { splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const { value: datePickerValue, shortcutsRange } = useDatePicker();

  const { value: searachSelectValue, searchSelectData } = useSearchSelect();

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      todo: 'running',
      self_manage: 1,
      status: ticketStatus.value,
    });

  const modelValue = defineModel<number>();

  const dataTableRef = useTemplateRef('dataTable');
  const ticketStatus = ref((route.params.status as string) || TicketModel.STATUS_TODO);
  const selectTicketIdList = shallowRef<IRowData[]>([]);
  const isShowBatchOperation = ref(false);

  watch(ticketStatus, () => {
    dataTableRef.value!.fetchData();
    dataTableRef.value!.resetSelection();
    router.replace({
      params: {
        status: ticketStatus.value,
      },
    });
  });

  const handleShowDetail = (data: IRowData) => {
    modelValue.value = data.id;
    stretchLayoutSplitScreen();
    appendSearchParams({
      viewId: data.id,
    });
  };

  const handleSelection = (data: IRowData[]) => {
    selectTicketIdList.value = data;
  };

  onMounted(() => {
    const searchParams = getSearchParams();
    if (Number(searchParams.viewId)) {
      modelValue.value = Number(route.query.viewId);
      stretchLayoutSplitScreen();
    }
  });
</script>
<style lang="less">
  .ticket-list-table-mode {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
