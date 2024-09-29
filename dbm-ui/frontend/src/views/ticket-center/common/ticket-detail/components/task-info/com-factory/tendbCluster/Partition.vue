<template>
  <RenderCom :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import RenderCom from '../common/mysql-partition/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.Partition>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_PARTITION,
    inheritAttrs: false,
  });
</script>
