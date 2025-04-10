<template>
  <DbPopconfirm
    :confirm-handler="handleTerminate"
    placement="bottom"
    :title="t('单据终止确认')"
    trigger="click"
    :width="400">
    <slot />
    <template #content>
      <div style="font-size: 12px; color: #63656e">
        <div>
          {{ t('操作：') }}
          <BkTag
            class="mr-4"
            theme="danger"
            type="stroke">
            {{ t('终止单据') }}
          </BkTag>
          <span>{{ t('终止后，单据将作废处理') }}</span>
        </div>
      </div>
    </template>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import { operateTimerFlow } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { messageSuccess } from '@utils';

  interface Props {
    data: FlowMode;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isSubmitting = ref(false);

  const handleTerminate = () => {
    isSubmitting.value = true;
    return operateTimerFlow({
      action: 'change',
      flow_id: props.data.id,
    })
      .then(() => {
        messageSuccess(t('操作成功'));
        eventBus.emit('refreshTicketStatus');
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
