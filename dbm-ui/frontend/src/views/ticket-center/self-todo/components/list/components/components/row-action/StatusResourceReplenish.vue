<template>
  <DbPopconfirm
    :confirm-handler="handleApproval"
    :content="t('提交后将会锁定资源，不可再重新分配，并进入下一个流程节点')"
    placement="bottom"
    :title="t('当前资源充足，确认提交？')"
    trigger="click"
    :width="400">
    <BkButton
      class="mr-8"
      :loading="isSubmitting"
      text
      theme="primary">
      {{ t('确认提交') }}
    </BkButton>
  </DbPopconfirm>
  <DbPopconfirm
    :confirm-handler="handleTerminate"
    :content="t('通过后将不可撤回')"
    placement="bottom"
    :title="t('确认终止单据？')"
    :width="400">
    <BkButton
      class="mr-8"
      :loading="isSubmitting"
      text
      theme="primary">
      {{ t('拒绝') }}
    </BkButton>
  </DbPopconfirm>
  <TicketClone :data="data" />
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

  import { messageSuccess } from '@utils';

  interface Props {
    data: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isSubmitting = ref(false);

  const handleApproval = () =>
    batchProcessTicket({
      action: 'APPROVE',
      ticket_ids: [props.data.id],
      params: {
        remark: t('确认提交'),
      },
    })
      .then(() => {
        messageSuccess(t('操作成功'));
        eventBus.emit('refreshTicketStatus');
      })
      .finally(() => {
        isSubmitting.value = false;
      });

  const handleTerminate = () => {
    isSubmitting.value = true;
    return batchProcessTicket({
      action: 'TERMINATE',
      ticket_ids: [props.data.id],
      params: {
        remark: t('终止单据'),
      },
    })
      .then(() => {
        eventBus.emit('refreshTicketStatus');
        messageSuccess(t('操作成功'));
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  };
</script>
