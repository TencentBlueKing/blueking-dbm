<template>
  <DumpData :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import DumpData from '../common/mysql-dump-data/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.DumpData>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_DUMP_DATA,
    inheritAttrs: false,
  });
</script>
