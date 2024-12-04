<template>
  <DbPopconfirm
    v-if="isCan"
    :confirm-handler="handleRevoke"
    :content="t('撤销后，单据将作废处理')"
    :title="t('确定撤销单据')">
    <BkButton theme="danger">
      {{ t('撤销单据') }}
    </BkButton>
  </DbPopconfirm>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { username } = useUserProfile();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const isCan = computed(() => props.data.status === TicketModel.STATUS_APPROVE && props.data.creator === username);

  const handleRevoke = () =>
    batchProcessTicket({
      action: 'TERMINATE',
      ticket_ids: [props.data.id],
    }).then(() => {
      eventBus.emit('refreshTicketStatus');
    });
</script>
