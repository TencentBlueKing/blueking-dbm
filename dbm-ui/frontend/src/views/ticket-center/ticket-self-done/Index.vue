<template>
  <div
    v-bk-loading="{ isLoading: isPreChecking }"
    class="ticket-self-done-page">
    <div class="header-action-box">
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('搜索单号、单据类型，集群，业务，备注，提单人...')"
        style="width: 550px" />
    </div>
    <TicketTable
      ref="dataTable"
      :data-source="dataSource" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { getTickets } from '@services/source/ticket';

  import useDetailPreCheck from '@views/ticket-center/common/hooks/use-detail-precheck';
  import useSearchSelect from '@views/ticket-center/common/hooks/use-search-select';
  import TicketTable from '@views/ticket-center/common/ticket-table/Index.vue';

  const route = useRoute();
  const { t } = useI18n();

  const { quickSearchData, quickSearchValue } = useSearchSelect();

  const isPreChecking = useDetailPreCheck({
    id: Number(route.params.ticketId),
    todo: 'done',
  });

  const dataSource = (params: ServiceParameters<typeof getTickets>) =>
    getTickets({
      ...params,
      todo: 'done',
    });
</script>
<style lang="less">
  .ticket-self-done-page {
    padding: 16px 24px;

    .header-action-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
