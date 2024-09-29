<template>
  <OpenArea :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import OpenArea from '../common/mysql-open-area/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.OpenArea>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_OPEN_AREA,
    inheritAttrs: false,
  });
</script>
