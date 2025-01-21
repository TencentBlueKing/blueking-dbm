<template>
  <DbCard
    v-model:collapse="isBaseinfoCardCollapse"
    mode="collapse"
    :title="t('基本信息')">
    <table
      v-if="localTicketData"
      class="ticket-base-info">
      <tbody>
        <tr>
          <td>{{ t('单号') }}:</td>
          <td>{{ localTicketData.id }}</td>
          <td>{{ t('单据状态') }}:</td>
          <td>
            <TicketStatusTag
              :data="localTicketData"
              small />
          </td>
          <td>{{ t('业务') }}:</td>
          <td>
            {{ localTicketData.bk_biz_name }}
          </td>
        </tr>
        <tr>
          <td>{{ t('已耗时') }}:</td>
          <td>
            <CostTimer
              :is-timing="localTicketData?.status === 'RUNNING'"
              :start-time="utcTimeToSeconds(localTicketData?.create_at)"
              :value="localTicketData?.cost_time || 0" />
          </td>
          <td>{{ t('单据类型') }}:</td>
          <td>{{ localTicketData.ticket_type_display }}</td>
          <td>{{ t('申请人') }}:</td>
          <td>{{ localTicketData.creator }}</td>
        </tr>
        <tr>
          <td>{{ t('申请时间') }}:</td>
          <td>{{ utcDisplayTime(localTicketData.create_at) }}</td>
        </tr>
      </tbody>
    </table>
  </DbCard>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketStatus } from '@services/source/ticket';

  import { useEventBus } from '@hooks';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const eventBus = useEventBus();

  const isBaseinfoCardCollapse = ref(false);
  const localTicketData = ref<TicketModel>();

  const { refresh: refreshTicketStatus } = useRequest(
    () => {
      if (!props.ticketData) {
        return Promise.reject();
      }
      return getTicketStatus({
        ticket_ids: `${props.ticketData.id}`,
      });
    },
    {
      manual: true,
      onSuccess(data) {
        if (localTicketData.value) {
          Object.assign(localTicketData.value, {
            status: data[localTicketData.value.id] as string,
          });
          if (!localTicketData.value.isFinished) {
            loopFetchTicketStatus();
          }
        }
      },
    },
  );

  watch(
    route,
    () => {
      isBaseinfoCardCollapse.value = route.name === 'ticketDetail';
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.ticketData,
    () => {
      if (props.ticketData) {
        localTicketData.value = new TicketModel(props.ticketData);
        refreshTicketStatus();
      }
    },
    {
      immediate: true,
    },
  );

  const refreshTicketData = () => {
    refreshTicketStatus();
  };

  const { start: loopFetchTicketStatus } = useTimeoutFn(() => {
    refreshTicketStatus();
  }, 3000);

  eventBus.on('refreshTicketStatus', refreshTicketData);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', refreshTicketData);
  });
</script>
<style lang="less">
  .ticket-base-info {
    table-layout: fixed;

    td {
      line-height: 32px;
      color: #313238;

      &:nth-child(2n + 1) {
        width: 150px;
        padding-right: 8px;
        text-align: right;
      }

      &:first-child {
        width: 100px;
      }
    }
  }
</style>
