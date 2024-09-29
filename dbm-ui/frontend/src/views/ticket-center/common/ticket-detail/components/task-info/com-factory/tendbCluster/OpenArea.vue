<template>
  <OpenArea :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import OpenArea from '../common/mysql-open-area/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.OpenArea>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_OPEN_AREA,
    inheritAttrs: false,
  });
</script>
