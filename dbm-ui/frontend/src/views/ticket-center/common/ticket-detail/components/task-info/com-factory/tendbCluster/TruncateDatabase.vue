<template>
  <TruncateData :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@/common/const';

  import TruncateData from '../common/mysql-truncate-data/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.TruncateData>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_TRUNCATE_DATABASE,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
