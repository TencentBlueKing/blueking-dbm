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

  export const TicketDetailTableKey: InjectionKey<{
    props: Props<Record<string, any>>;
  }> = Symbol('TicketDetailTableKey');

  export { InfoTableColumn };
</script>

<script setup lang="ts" generic="T extends Record<string, any>">
  export interface Props<IRowData> {
    data: IRowData[];
    rowKey: string;
  }

  const props = defineProps<Props<T>>();

  defineSlots<{
    default: () => VNode;
  }>();

  const attrs = useAttrs();

  provide(TicketDetailTableKey, {
    props,
  });
</script>
