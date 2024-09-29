<template>
  <AccountRuleChange :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import AccountRuleChange from '../common/mysql-account-rule-change/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.AccountRuleChange>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_ACCOUNT_RULE_CHANGE,
    inheritAttrs: false,
  });
</script>
