<template>
  <DbCard
    mode="collapse"
    :title="t('基本信息')">
    <table class="ticket-base-info">
      <tbody>
        <tr>
          <td>{{ t('单号') }}:</td>
          <td>{{ ticketData.id }}</td>
          <td>{{ t('单据状态') }}:</td>
          <td>
            <BkTag :theme="ticketData.tagTheme">
              {{ t(ticketData.statusText) }}
            </BkTag>
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

  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    ticketData: TicketModel<unknown>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
<style lang="less">
  .ticket-base-info {
    td {
      width: 18%;
      line-height: 32px;
      color: #313238;

      &:nth-child(2n + 1) {
        width: 12%;
        padding-right: 8px;
        text-align: right;
      }
    }
  }
</style>
