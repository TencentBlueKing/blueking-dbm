<template>
  <PrimaryTable
    v-bind="{ ...attrs }"
    :data="data"
    :max-height="500"
    resizable
    :row-key="rowKey">
    <slot />
  </PrimaryTable>
</template>

<script lang="ts">
  import type { InjectionKey, VNode } from 'vue';

  import InfoTableColumn from './InfoTableColumn.vue';

  interface Props {
    data: Record<string, any>[];
    rowKey: string;
  }

  export const TicketDetailTableKey: InjectionKey<{
    props: Props;
  }> = Symbol('TicketDetailTableKey');

  export { InfoTableColumn };
</script>

<script setup lang="ts">
  const props = defineProps<Props>();

  defineSlots<{
    default: () => VNode;
  }>();

  const attrs = useAttrs();

  provide(TicketDetailTableKey, {
    props,
  });
</script>
