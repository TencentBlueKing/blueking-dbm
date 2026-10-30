<template>
  <ClusterOperation :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type VictoriaMetrics } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ClusterOperation from '../common/ClusterOperation.vue';

  interface Props {
    ticketDetails: TicketModel<VictoriaMetrics.Disable>;
  }

  defineOptions({
    name: TicketTypes.K8S_VICTORIAMETRICS_DISABLE,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
