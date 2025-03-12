<template>
  <BkSideslider
    v-model:is-show="moduleValue"
    width="1300">
    <template #header>
      <div>【{{ ip }}】{{ t('操作记录') }}</div>
    </template>
    <div class="all-host-record">
      <BkLoading
        :loading="tableLoading"
        :z-index="2">
        <BkTable
          ref="tableRef"
          :data="machineEventList?.results"
          :show-overflow="false">
          <BkTableColumn
            field="events"
            :label="t('操作类型')"
            :width="130">
            <template #default="{ data }: { data: MachineEventModel }">
              {{ data.eventDisplay }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="updater"
            :label="t('操作人')"
            show-overflow="tooltip"
            :width="120">
          </BkTableColumn>
          <BkTableColumn
            field="updateAtDisplay"
            :label="t('操作时间')"
            :width="180">
          </BkTableColumn>
          <BkTableColumn
            field="bk_biz_name"
            :label="t('所属业务')"
            :width="100">
          </BkTableColumn>
          <BkTableColumn
            field="ticket"
            :label="t('关联单据')"
            :min-width="200">
            <template #default="{ data }: { data: MachineEventModel }">
              <RouterLink
                v-if="data.ticket"
                target="_blank"
                :to="{
                  name: 'bizTicketManage',
                  params: {
                    ticketId: data.ticket,
                  },
                }">
                {{ data.ticket_type_display }}
              </RouterLink>
              <span v-else>--</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="clusters"
            :label="t('集群')"
            :min-width="200"
            show-overflow="tooltip">
            <template #default="{ data }: { data: MachineEventModel }">
              {{ data.clusters.length ? data.clusters.map((item) => item.immute_domain).join(', ') : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="event"
            :label="t('操作明细')"
            :width="300">
            <template #default="{ data }: { data: MachineEventModel }">
              <OperationDetail :data="data" />
            </template>
          </BkTableColumn>
        </BkTable>
      </BkLoading>
    </div>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MachineEventModel from '@services/model/db-resource/machineEvent';
  import { getMachineEvents } from '@services/source/dbdirty';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';

  interface Props {
    ip: string;
  }

  const props = defineProps<Props>();

  const moduleValue = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();

  const {
    data: machineEventList,
    loading: tableLoading,
    run: runGetMachineEvents,
  } = useRequest(getMachineEvents, {
    manual: true,
  });

  watch(
    () => props.ip,
    () => {
      runGetMachineEvents({
        ips: props.ip,
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
