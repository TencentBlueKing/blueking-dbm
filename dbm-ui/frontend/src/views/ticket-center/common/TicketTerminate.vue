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

  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import ProcessFailedTerminate from '@views/ticket-center/common/action-confirm/ProcessFailedTerminate.vue';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { username } = useUserProfile();
  const { t } = useI18n();

  const isRender = computed(() => {
    return (
      [
        TicketModel.STATUS_APPROVE,
        TicketModel.STATUS_FAILED,
        TicketModel.STATUS_INNER_TODO,
        TicketModel.STATUS_RESOURCE_REPLENISH,
        TicketModel.STATUS_TIMER,
        TicketModel.STATUS_TODO,
      ].includes(props.data.status) &&
      (props.data.todo_helpers.includes(username) || props.data.todo_operators.includes(username))
    );
  });
</script>
