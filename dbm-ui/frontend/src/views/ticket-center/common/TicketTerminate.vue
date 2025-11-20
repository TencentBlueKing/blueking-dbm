<template>
  <ProcessFailedTerminate
    v-if="isRender"
    :data="data">
    <BkButton theme="danger">
      {{ t('终止单据') }}
    </BkButton>
  </ProcessFailedTerminate>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getTicketStatus } from '@services/source/ticket';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import ProcessFailedTerminate from '@views/ticket-center/common/action-confirm/ProcessFailedTerminate.vue';

  import { useTimeoutFn } from '@vueuse/core';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { isSuperuser, username } = useUserProfile();
  const { t } = useI18n();

  const eventBus = useEventBus();

  const localTicketData = ref<TicketModel>();

  const isRender = computed(() => {
    return (
      localTicketData.value &&
      [
        TicketModel.STATUS_FAILED,
        TicketModel.STATUS_INNER_TODO,
        TicketModel.STATUS_RESOURCE_REPLENISH,
        TicketModel.STATUS_TIMER,
        TicketModel.STATUS_TODO,
      ].includes(localTicketData.value.status) &&
      (isSuperuser ||
        localTicketData.value.todo_helpers.includes(username) ||
        localTicketData.value.todo_operators.includes(username))
    );
  });

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

  const { start: loopFetchTicketStatus } = useTimeoutFn(() => {
    refreshTicketStatus();
  }, 3000);

  eventBus.on('refreshTicketStatus', refreshTicketStatus);

  onBeforeUnmount(() => {
    eventBus.off('refreshTicketStatus', refreshTicketStatus);
  });
</script>
