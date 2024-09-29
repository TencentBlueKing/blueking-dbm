<template>
  <AuthorizeRule :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import AuthorizeRule from '../common/mysql-authorize-rules/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.AuthorizeRules>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_AUTHORIZE_RULES,
    inheritAttrs: false,
  });
</script>
