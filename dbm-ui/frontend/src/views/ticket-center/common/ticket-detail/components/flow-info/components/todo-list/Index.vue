<template>
  <div v-if="ticketData">
    <template
      v-for="(todoItem, index) in data"
      :key="index">
      <TypeApprove
        :data="todoItem"
        :flow-data="flowData"
        :ticket-data="ticketData" />
      <TypeResourceReplenish
        :data="todoItem"
        :flow-data="flowData"
        :ticket-data="ticketData" />
      <TypeItsm
        :data="todoItem"
        :flow-data="flowData"
        :ticket-data="ticketData" />
      <TypeInnerApprove
        :data="todoItem"
        :flow-data="flowData"
        :ticket-data="ticketData" />
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import FlowMode from '@services/model/ticket/flow';
  import { getTicketDetails } from '@services/source/ticket';

  import TypeApprove from './type-approve/Index.vue';
  import TypeInnerApprove from './type-inner-approve/Index.vue';
  import TypeItsm from './type-itsm/Index.vue';
  import TypeResourceReplenish from './type-resource-replenish/Index.vue';

  interface Props {
    flowData: FlowMode<unknown, any>;
    data: FlowMode['todos'];
  }

  const props = defineProps<Props>();

  const { data: ticketData } = useRequest(
    (params) =>
      getTicketDetails(params, {
        cache: 1000,
      }),
    {
      defaultParams: [
        {
          id: props.flowData.ticket,
        },
      ],
    },
  );
</script>
