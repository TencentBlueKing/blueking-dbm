<template>
  <AccountRuleChange
    :account-type="AccountTypes.TENDBCLUSTER"
    :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { AccountTypes, TicketTypes } from '@common/const';

  import AccountRuleChange from '../common/mysql-account-rule-change/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.AccountRuleChange>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_ACCOUNT_RULE_CHANGE,
    inheritAttrs: false,
  });
</script>
