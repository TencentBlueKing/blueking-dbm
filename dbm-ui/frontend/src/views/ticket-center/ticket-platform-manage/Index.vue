<template>
  <div
    v-bk-loading="{ isLoading: isPreChecking }"
    class="ticket-platform-manage-page">
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
    <TicketTable
      ref="dataTable"
      :data-source="dataSource">
      <template #action>
        <BkTableColumn
          fixed="right"
          :label="t('操作')"
          width="80">
          <template #default="{ data }: { data: TicketModel }">
            <TicketClone
              v-if="data"
              :data="data" />
          </template>
        </BkTableColumn>
      </template>
    </TicketTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import useDatePicker from '@views/ticket-center/common/hooks/use-date-picker';
  import useDetailPreCheck from '@views/ticket-center/common/hooks/use-detail-precheck';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TicketTable from '@views/ticket-center/common/ticket-table/Index.vue';
  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

  const route = useRoute();
  const { t } = useI18n();

  const { shortcutsRange, value: datePickerValue } = useDatePicker();

  const { searchSelectData, value: searachSelectValue } = useSearchSelect();

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
    });

  const isPreChecking = useDetailPreCheck({
    id: Number(route.params.ticketId),
  });
</script>
<style lang="less">
  .ticket-platform-manage-page {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
