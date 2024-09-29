<template>
  <Component
    :is="detailsComp"
    :key="data.id"
    :ticket-details="data" />
</template>
<script setup lang="tsx">
  import _ from 'lodash';

  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import DefaultDetails from './Default.vue';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const allModule = import.meta.glob<{
    default: {
      name: TicketTypes;
    };
  }>(['./*/*.vue', '!./common', '!./components'], {
    eager: true,
  });

  const detailsComp = computed(() => {
    const renderModule = _.find(
      Object.values(allModule),
      (moduleItem) => moduleItem.default.name === props.data.ticket_type,
    );

    if (renderModule) {
      return renderModule.default;
    }

    return DefaultDetails;
  });
</script>
