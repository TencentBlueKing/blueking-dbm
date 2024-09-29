<template>
  <div>
    <template
      v-for="(todoItem, index) in data"
      :key="index">
      <TypeApprove
        :data="todoItem"
        :flow-data="flowData" />
      <TypeResourceReplenish
        :data="todoItem"
        :flow-data="flowData" />
      <TypeItsm
        :data="todoItem"
        :flow-data="flowData" />
      <TypeInnerApprove
        :data="todoItem"
        :flow-data="flowData" />
    </template>
  </div>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import TypeApprove from './type-approve/Index.vue';
  import TypeInnerApprove from './type-inner-approve/Index.vue';
  import TypeItsm from './type-itsm/Index.vue';
  import TypeResourceReplenish from './type-resource-replenish/Index.vue';

  interface Props {
    flowData: FlowMode<unknown, any>;
    data: FlowMode['todos'];
  }

  defineProps<Props>();
</script>
