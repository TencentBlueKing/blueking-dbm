<template>
  <BkLoading
    :loading="isLoading"
    style="min-height: 60px">
    <FlowCollapse>
      <template #header>
        <div class="related-ticket-title-main">
          <span class="pre-title">{{ t('关联单据') }}</span>
          <BkButton
            v-bk-tooltips="t('跳转查看单据')"
            class="ml-4"
            text
            theme="primary"
            @click.stop="handleGoTicketDetail">
            - {{ ticketData?.ticket_type_display }}({{ ticketId }})
          </BkButton>
        </div>
      </template>
      <div class="ticket-details-relate-ticket-flow">
        <RenderFlow
          v-if="ticketData"
          style="margin-left: 25px"
          :ticket-detail="ticketData" />
      </div>
    </FlowCollapse>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import { getTicketDetails } from '@services/source/ticket';

  import RenderFlow from '@views/ticket-center/common/ticket-detail/components/flow-info/RenderFlow.vue';

  import { getBusinessHref } from '@utils';

  import FlowCollapse from '../flow-type-common/components/FlowCollapse.vue';

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
  .related-ticket-title-main {
    font-weight: bold;
    color: #313238;

    .pre-title {
      margin-left: 8px;
      font-weight: 700;
    }
  }

  .ticket-details-relate-ticket-flow {
    position: relative;
    padding-bottom: 20px;
    font-size: 12px;
    line-height: 19px;
    color: #63656e;

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

    .db-time-line-icon {
      background-color: #f5f7fa;
    }
  }
</style>
