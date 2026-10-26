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
    const renderResourcePoolModule = _.find(
      Object.values(resourcePoolModule),
      (moduleItem) => moduleItem.default.name === props.data.ticket_type,
    );

    const renderModule = _.find(
      Object.values(allModule),
      (moduleItem) => moduleItem.default.name === props.data.ticket_type,
    );

    // 同一单据类型在两个目录各有一份时：手动录入主机的单据（含历史单）details 按主机对象落库，
    // 资源池模板按 resource_spec.*.hosts 读会抛错，此时用普通目录那份；其余保持资源池优先
    const { ip_source: ipSource } = props.data.details as { ip_source?: string };
    if (renderResourcePoolModule && renderModule && ipSource === 'manual_input') {
      return renderModule.default;
    }

    if (renderResourcePoolModule) {
      return renderResourcePoolModule.default;
    }

    if (renderModule) {
      return renderModule.default;
    }

    return DefaultDetails;
  });
</script>
