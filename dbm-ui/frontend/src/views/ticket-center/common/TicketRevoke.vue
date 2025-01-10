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
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketStatus } from '@services/source/ticket';
  import { batchProcessTicket } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { username } = useUserProfile();

  const { t } = useI18n();
  const eventBus = useEventBus();

  const localTicketData = ref<TicketModel>();

  const isCan = computed(
    () => localTicketData.value?.status === TicketModel.STATUS_APPROVE && props.data.creator === username,
  );

  const { refresh: refreshTicketStatus } = useRequest(
    () => {
      if (!props.data) {
        return Promise.reject();
      }
      return getTicketStatus({
        ticket_ids: `${props.data.id}`,
      });
    },
    {
      manual: true,
      onSuccess(data) {
        localTicketData.value!.status = data[props.data.id] as TicketModel['status'];
        if (!localTicketData.value!.isFinished) {
          loopFetchTicketStatus();
        }
      },
    },
  );

  watch(
    () => props.data,
    () => {
      if (props.data) {
        localTicketData.value = new TicketModel(props.data);
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

  const handleRevoke = () =>
    batchProcessTicket({
      action: 'TERMINATE',
      ticket_ids: [props.data.id],
    }).then(() => {
      eventBus.emit('refreshTicketStatus');
    });
</script>
