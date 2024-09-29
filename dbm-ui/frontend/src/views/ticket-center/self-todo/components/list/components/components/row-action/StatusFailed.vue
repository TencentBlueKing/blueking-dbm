<template>
  <TicketClone :data="data" />
</template>
<script setup lang="ts">
  import TicketModel from '@services/model/ticket/ticket';

  import TicketClone from '@views/ticket-center/common/TicketClone.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  defineProps<Props>();
</script>
