<template>
  <BkSideslider
    v-model:is-show="moduleValue"
    width="1400">
    <template #header>
      <div>【{{ data.ip }}】{{ t('操作记录') }}</div>
    </template>
    <div class="all-host-record">
      <BkLoading
        :loading="tableLoading"
        :z-index="2">
        <PrimaryTable
          ref="tableRef"
          :data="machineEventList"
          row-key="id">
          <TableColumn
            col-key="events"
            :title="t('操作类型')"
            :width="130">
            <template #default="{ row }: { row : MachineEventModel }">
              {{ row.eventDisplay }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="updater"
            :title="t('操作人')"
            :width="120">
          </TableColumn>
          <TableColumn
            col-key="updateAtDisplay"
            :title="t('操作时间')"
            :width="180">
          </TableColumn>
          <TableColumn
            col-key="bk_biz_name"
            :title="t('所属业务')"
            :width="100">
          </TableColumn>
          <TableColumn
            col-key="ticket"
            :min-width="200"
            :title="t('关联单据')">
            <template #default="{ row }: { row : MachineEventModel }">
              <template v-if="row.ticket">
                <TicketStatusTag
                  :data="{
                    status: row.ticket_status,
                    statusText: row.statusText,
                  }" />
                <RouterLink
                  class="ml-4"
                  target="_blank"
                  :to="{
                    name: 'bizTicketManage',
                    params: {
                      ticketId: row.ticket,
                    },
                  }">
                  {{ row.ticket_type_display }}[{{ row.ticket }}]
                </RouterLink>
              </template>
              <span v-else>--</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="clusters"
            :min-width="300"
            :title="t('集群')">
            <template #default="{ row }: { row : MachineEventModel }">
              {{ row.clusters.length ? row.clusters.map((item) => item.immute_domain).join(', ') : '--' }}
            </template>
          </TableColumn>
          <TableColumn
            col-key="event"
            :title="t('操作明细')"
            :width="300">
            <template #default="{ row }: { row : MachineEventModel }">
              <OperationDetail :data="row" />
            </template>
          </TableColumn>
        </PrimaryTable>
      </BkLoading>
    </div>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MachineEventModel from '@services/model/db-resource/machineEvent';
  import { getHostCurrentEvent } from '@services/source/dbdirty';

  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';

  interface Props {
    data: {
      bk_host_id: number;
      ip: string;
    };
  }

  const props = defineProps<Props>();

  const moduleValue = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();

  const {
    data: machineEventList,
    loading: tableLoading,
    run: runGetHostCurrentEvent,
  } = useRequest(getHostCurrentEvent, {
    manual: true,
  });

  watch(
    () => props.data.bk_host_id,
    () => {
      runGetHostCurrentEvent({
        bk_host_id: props.data.bk_host_id,
      });
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .all-host-record {
    padding: 12px;
  }
</style>
