<template>
  <div class="resource-pool-operation-record-page">
    <div class="header-action mb-16">
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="getMachineEvents"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="id"
      @filter-change="handleFilterChange">
      <TableColumn
        col-key="ips"
        :filter="columnFilter?.ips"
        fixed="left"
        title="IP"
        :width="150">
        <template #default="{ row }: { row: MachineEventModel }">
          {{ row.ip || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="events"
        :filter="columnFilter?.events"
        :title="t('操作类型')"
        :width="130">
        <template #default="{ row }: { row: MachineEventModel }">
          {{ row.eventDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updater"
        :filter="columnFilter?.updater"
        :title="t('操作人')"
        :width="120">
      </TableColumn>
      <TableColumn
        col-key="create_at"
        :filter="columnFilter?.create_at"
        :title="t('操作时间')"
        :width="200">
        <template #default="{ row }: { row: MachineEventModel }">
          {{ row.createAtDisplay }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_biz_id"
        :filter="columnFilter?.bk_biz_id"
        :min-width="180"
        :title="t('所属业务')">
        <template #default="{ row }: { row: MachineEventModel }">
          {{ row.bk_biz_name }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="ticket_id"
        :filter="columnFilter?.ticket_id"
        :min-width="200"
        :title="t('关联单据')">
        <template #default="{ row }: { row: MachineEventModel }">
          <template v-if="row.ticket">
            <TicketStatusTag
              :data="{
                status: row.ticket_status,
                statusText: row.statusText,
              }" />
            <BkButton
              class="ml-4"
              text
              theme="primary"
              @click="handleToTicket(row)">
              {{ row.ticket_type_display }}[{{ row.ticket }}]
            </BkButton>
          </template>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="clusters"
        :filter="columnFilter?.domain"
        :min-width="300"
        :title="t('集群')">
        <template #default="{ row }: { row: MachineEventModel }">
          {{ row.clusters.length ? row.clusters.map((item) => item.immute_domain).join(', ') : '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="event"
        :min-width="300"
        :title="t('操作明细')">
        <template #default="{ row }: { row: MachineEventModel }">
          <OperationDetail :data="row" />
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MachineEventModel from '@services/model/db-resource/machineEvent';
  import { getMachineEvents } from '@services/source/dbdirty';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';

  import { useColumnFilter } from './useColumnFilter';
  import { useQuickSearch } from './useQuickSearch';

  const { t } = useI18n();
  const router = useRouter();
  const { quickSearchData, quickSearchValue } = useQuickSearch();
  const { data: columnFilter } = useColumnFilter();

  const tableRef = useTemplateRef('tableRef');

  // 获取数据
  const fetchData = () => {
    tableRef.value!.fetchData(quickSearchValue.value);
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, any>) => {
    quickSearchValue.value = filterValue;
  };

  const handleToTicket = (data: MachineEventModel) => {
    const taskHistoryListRoute = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: data.ticket,
      },
    });
    const href = taskHistoryListRoute.href.replace(/\/(\d+)\//, `/${data.bk_biz_id}/`);
    window.open(href, '_blank');
  };
</script>

<style lang="less">
  .resource-pool-operation-record-page {
    .header-action {
      display: flex;
    }
  }
</style>
