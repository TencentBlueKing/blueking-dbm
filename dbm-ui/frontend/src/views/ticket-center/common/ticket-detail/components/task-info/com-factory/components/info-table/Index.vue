<template>
  <PrimaryTable
    v-bind="{ ...attrs, ...props }"
    :max-height="500">
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
    // eslint-disable-next-line vue/no-unused-properties
    data: IRowData[];
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
