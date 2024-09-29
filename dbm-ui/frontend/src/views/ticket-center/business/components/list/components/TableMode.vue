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
            <TicketClone
              v-if="data"
              :data="data" />
          </template>
        </BkTableColumn>
      </template>
    </TableModeTable>
  </div>
</template>
<script setup lang="ts">
  import { onMounted } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import { useStretchLayout, useUrlSearch } from '@hooks';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TableModeTable from '@views/ticket-center/common/TableModeTable.vue';
  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

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
    });

  const modelValue = defineModel<number>();

  const handleShowDetail = (data: IRowData) => {
    modelValue.value = data.id;
    stretchLayoutSplitScreen();
    appendSearchParams({
      viewId: data.id,
    });
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
