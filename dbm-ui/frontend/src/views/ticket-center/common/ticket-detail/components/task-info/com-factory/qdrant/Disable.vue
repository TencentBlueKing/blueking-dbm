<template>
  <ClusterOperation :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Qdrant } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ClusterOperation from '../common/ClusterOperation.vue';

  interface Props {
    ticketDetails: TicketModel<Qdrant.Disable>;
  }

  defineOptions({
    name: TicketTypes.K8S_QDRANT_DISABLE,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
