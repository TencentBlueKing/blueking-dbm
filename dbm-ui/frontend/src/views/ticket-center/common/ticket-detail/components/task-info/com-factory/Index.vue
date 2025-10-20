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

  const resourcePoolModule = import.meta.glob<{
    default: {
      name: TicketTypes;
    };
  }>(
    [
      './resource-pool-strategy/*/*.vue',
      './resource-pool-strategy/*/*/*.vue',
      '!./resource-pool-strategy/*/*/components',
    ],
    {
      eager: true,
    },
  );

  const allModule = import.meta.glob<{
    default: {
      name: TicketTypes;
    };
  }>(['./*/*.vue', './*/*/*.vue', '!./common', '!./components'], {
    eager: true,
  });

  const detailsComp = computed(() => {
    const { details: resourcePoolDetails, ticket_type: resourcePoolTicketType } = props.data as TicketModel<{
      ip_recycle?: { ip_dest: string };
      ip_source?: string;
    }>;

    const isResourcePool =
      // 资源池回收
      resourcePoolDetails.ip_recycle?.ip_dest === 'resource' ||
      // 主机来源于资源池
      resourcePoolDetails.ip_source === 'resource_pool' ||
      // 平台资源池单据
      /^RESOURCE_/.test(resourcePoolTicketType);

    const renderResourcePoolModule = _.find(
      Object.values(resourcePoolModule),
      (moduleItem) => moduleItem.default.name === props.data.ticket_type,
    );

    if (isResourcePool && renderResourcePoolModule) {
      return renderResourcePoolModule.default;
    }

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
