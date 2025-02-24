<template>
  <BkLoading
    :loading="isLoading"
    style="min-height: 60px">
    <div class="ticket-details-relate-ticket-flow">
      <div class="wrapper">
        <div class="title">
          <div class="flag">
            <DbIcon type="links" />
          </div>
          <span>{{ t('关联单据') }} - {{ ticketData?.ticket_type_display }}</span>
          <BkButton
            v-bk-tooltips="t('跳转查看单据')"
            class="ml-4"
            text
            theme="primary"
            @click="handleGoTicketDetail">
            ({{ ticketId }})
          </BkButton>
        </div>
        <RenderFlow
          v-if="ticketData"
          style="margin-left: 25px"
          :ticket-detail="ticketData" />
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import { getTicketDetails } from '@services/source/ticket';

  import RenderFlow from '@views/ticket-center/common/ticket-detail/components/flow-info/RenderFlow.vue';

  import { getBusinessHref } from '@utils';

  interface Props {
    ticketId: number;
  }

  const props = defineProps<Props>();

  const router = useRouter();

  const { t } = useI18n();

  const { data: ticketData, loading: isLoading } = useRequest(getTicketDetails, {
    defaultParams: [
      {
        id: props.ticketId,
      },
    ],
  });

  const handleGoTicketDetail = () => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: props.ticketId,
      },
    });

    window.open(getBusinessHref(href, ticketData.value?.bk_biz_id));
  };
</script>
<style lang="less">
  .ticket-details-relate-ticket-flow {
    position: relative;
    padding-bottom: 20px;
    padding-left: 24px;
    font-size: 12px;
    line-height: 19px;
    color: #63656e;

    .wrapper {
      width: 550px;
      padding: 12px 16px;
      background-color: #ebf2ff;

      .flag {
        display: inline-flex;
        width: 24px;
        height: 24px;
        margin-right: 4px;
        font-size: 14px;
        font-weight: bold;
        color: #3a84ff;
        background: #e1ecff;
        border-radius: 50%;
        align-items: center;
        justify-content: center;
      }

      .title {
        margin-bottom: 12px;
        font-weight: bold;
        color: #313238;
      }

      .db-time-line-icon {
        background-color: #ebf2ff;
      }
    }
  }
</style>
