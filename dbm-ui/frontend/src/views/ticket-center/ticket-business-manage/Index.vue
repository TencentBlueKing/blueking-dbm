<template>
  <div
    v-bk-loading="{ isLoading: isPreChecking }"
    class="ticket-business-manage-page">
    <div class="header-action-box">
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        style="width: 550px" />
    </div>
    <TicketTable
      ref="dataTable"
      :data-source="dataSource"
      :exclude-column="['bk_biz_id']">
      <template #action>
        <TableColumn
          col-key="action"
          fixed="right"
          :title="t('操作')"
          width="80">
          <template #default="{ row }: { row: TicketModel }">
            <TicketClone
              v-if="row"
              :data="row" />
          </template>
        </TableColumn>
      </template>
    </TicketTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTickets } from '@services/source/ticket';

  import useDetailPreCheck from '@views/ticket-center/common/hooks/use-detail-precheck';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TicketTable from '@views/ticket-center/common/ticket-table/Index.vue';
  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

  const route = useRoute();

  const { t } = useI18n();

  const { quickSearchData, quickSearchValue } = useSearchSelect({
    exclude: ['bk_biz_id'],
  });

  const isPreChecking = useDetailPreCheck({
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    id: Number(route.params.ticketId),
  });

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
</script>
<style lang="less">
  .ticket-business-manage-page {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
