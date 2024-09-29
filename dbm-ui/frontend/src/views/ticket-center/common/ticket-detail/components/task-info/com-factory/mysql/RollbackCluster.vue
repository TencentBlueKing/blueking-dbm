<template>
  <Rollback :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import Rollback from '../common/mysql-rollback/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.RollbackCluster>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_ROLLBACK_CLUSTER,
    inheritAttrs: false,
  });
</script>
