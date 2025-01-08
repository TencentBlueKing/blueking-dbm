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
      :data-source="dataSource"
      :row-class="rowClass">
      <template #action>
        <BkTableColumn
          field="createAtDisplay"
          fixed="right"
          :label="t('操作')"
          width="160">
          <template #default="{ data }: { data: IRowData }">
            <TicketClone
              v-if="data"
              :data="data" />
            <TicketDetailLink
              v-if="data"
              class="ml-8"
              :data="data" />
          </template>
        </BkTableColumn>
      </template>
    </TableModeTable>
  </div>
</template>
<script setup lang="ts">
  import { onActivated } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import { useUrlSearch } from '@hooks';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TableModeTable from '@views/ticket-center/common/TableModeTable.vue';
  import TicketClone from '@views/ticket-center/common/TicketClone.vue';
  import TicketDetailLink from '@views/ticket-center/common/TicketDetailLink.vue';

  type IRowData = TicketModel<unknown>;

  const route = useRoute();
  const { t } = useI18n();

  const { removeSearchParam } = useUrlSearch();

  const { value: datePickerValue, shortcutsRange } = useDatePicker();

  const { value: searachSelectValue, searchSelectData } = useSearchSelect();

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      self_manage: 0,
    });

  const selectTicketId = ref(0);

  const rowClass = (params: TicketModel) => (params.id === selectTicketId.value ? 'select-row' : '');

  onActivated(() => {
    selectTicketId.value = Number(route.query.selectId);
    removeSearchParam('selectId');
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
