<template>
  <AuthorizeRule :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import AuthorizeRule from '../common/mysql-authorize-rules/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.AuthorizeRules>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_EXCEL_AUTHORIZE_RULES,
    inheritAttrs: false,
  });
</script>
