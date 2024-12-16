<template>
  <DbCard
    v-model:collapse="isBaseinfoCardCollapse"
    mode="collapse"
    :title="t('基本信息')">
    <table class="ticket-base-info">
      <tbody>
        <tr>
          <td>{{ t('单号') }}:</td>
          <td>{{ ticketData.id }}</td>
          <td>{{ t('单据状态') }}:</td>
          <td>
            <TicketStatusTag
              :data="ticketData"
              small />
          </td>
          <td>{{ t('已耗时') }}:</td>
          <td>
            <CostTimer
              :is-timing="ticketData?.status === 'RUNNING'"
              :start-time="utcTimeToSeconds(ticketData?.create_at)"
              :value="ticketData?.cost_time || 0" />
          </td>
        </tr>
        <tr>
          <td>{{ t('单据类型') }}:</td>
          <td>{{ ticketData.ticket_type_display }}</td>
          <td>{{ t('申请人') }}:</td>
          <td>{{ ticketData.creator }}</td>
          <td>{{ t('申请时间') }}:</td>
          <td>{{ utcDisplayTime(ticketData.create_at) }}</td>
        </tr>
      </tbody>
    </table>
  </DbCard>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    ticketData: TicketModel;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();

  const isBaseinfoCardCollapse = ref(false);

  watch(
    route,
    () => {
      isBaseinfoCardCollapse.value = route.name === 'ticketDetail';
    },
    {
      immediate: true,
    },
  );
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
