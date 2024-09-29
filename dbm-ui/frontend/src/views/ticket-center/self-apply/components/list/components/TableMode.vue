<template>
  <div class="ticket-list-table-mode">
    <div class="header-action-box">
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
      :data-source="dataSource">
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
          field="createAtDisplay"
          fixed="right"
          :label="t('操作')"
          width="160">
          <template #default="{ data }: { data: IRowData }">
            <BkButton
              class="ml-8"
              text
              theme="primary">
              {{ t('再次提单') }}
            </BkButton>
            <DbPopconfirm
              v-if="data.status === TicketModel.STATUS_PENDING"
              class="ml-8"
              :confirm-handler="() => handleApproval(data)"
              :content="t('通过后将不可撤回')"
              :title="t('确认撤销单据？')">
              <BkButton
                text
                theme="primary">
                {{ t('撤销') }}
              </BkButton>
            </DbPopconfirm>
          </template>
        </BkTableColumn>
      </template>
    </TableModeTable>
  </div>
</template>
<script setup lang="ts">
  import { onMounted, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useStretchLayout, useUrlSearch } from '@hooks';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TableModeTable from '@views/ticket-center/common/TableModeTable.vue';

  import { messageSuccess } from '@utils';

  type IRowData = TicketModel<unknown>;

  const route = useRoute();

  const { t } = useI18n();
  const { appendSearchParams, getSearchParams } = useUrlSearch();

  const { splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const { value: datePickerValue, shortcutsRange } = useDatePicker();

  const { value: searachSelectValue, searchSelectData } = useSearchSelect();

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      self_manage: 0,
    });

  const modelValue = defineModel<number>();

  const tableRef = useTemplateRef('dataTable');

  const handleShowDetail = (data: IRowData) => {
    modelValue.value = data.id;
    stretchLayoutSplitScreen();
    appendSearchParams({
      viewId: data.id,
    });
  };

  const handleApproval = (data: IRowData) =>
    batchProcessTicket({
      action: 'APPROVE',
      ticket_ids: [data.id],
    }).then(() => {
      messageSuccess(t('操作成功'));
      tableRef.value?.fetchData();
    });

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
