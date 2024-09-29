<template>
  <DbPopconfirm
    :confirm-handler="handleApproval"
    placement="bottom"
    :title="t('单据重试确认')"
    trigger="click"
    :width="350">
    <slot />
    <template #content>
      <div>
        {{ t('操作：') }}
        <BkTag
          class="mr-4"
          theme="success"
          type="stroke">
          {{ t('重试') }}
        </BkTag>
        <span>{{ t('重试后，单据将再次尝试继续执行') }}</span>
      </div>
    </template>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { retryFlow } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { messageSuccess } from '@utils';

  interface Props {
    data: TicketModel;
    flowData: FlowMode;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isSubmitting = ref(false);

  const handleApproval = () => {
    isSubmitting.value = true;
    return Promise.resolve()
      .then(() =>
        retryFlow({
          id: props.data.id,
          flow_id: props.flowData.id,
        }),
      )
      .then(() => {
        messageSuccess(t('操作成功'));
        eventBus.emit('refreshTicketStatus');
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
