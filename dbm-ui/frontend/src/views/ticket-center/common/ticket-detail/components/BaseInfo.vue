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
          <td>
            <bk-user-display-name :user-id="localTicketData.creator" />
          </td>
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
  import { useRoute } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';
  import TicketStatusTag from '@components/ticket-status-tag/Index.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    /** 父组件轮询得到的最新单据状态 */
    status: TicketModel['status'];
    ticketData: TicketModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();

  const isBaseinfoCardCollapse = ref(false);
  // 用最新状态覆盖详情数据里的状态，供状态标签与计时器使用
  const localTicketData = computed(() => {
    const data = new TicketModel(props.ticketData);
    data.status = props.status;
    return data;
  });

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
