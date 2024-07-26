<template>
  <SmartAction>
    <Component
      :is="components.RenderData"
      class="mt16 mb-20"
      @batch-edit="(obj) => emits('batchEdit', obj)"
      @batch-select-cluster="() => emits('showSelector')">
      <Component
        :is="components.RenderDataRow"
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        @add="(payload: Array<IDataRow>) => emits('add', index, payload)"
        @remove="() => emits('remove', index)" />
    </Component>
    <template #action>
      <slot />
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { RollbackClusterTypes } from '@services/model/ticket/details/mysql';

  import type { IDataRow } from '../../Index.vue';

  import ExistCluster from './exist-cluster/Index.vue';
  import ExistClusterRow from './exist-cluster/Row.vue';
  import NewCluster from './new-cluster/Index.vue';
  import NewClusterRow from './new-cluster/Row.vue';
  import OriginCluster from './origin-cluster/Index.vue';
  import OriginClusterRow from './origin-cluster/Row.vue';

  interface Props {
    data: IDataRow[];
    rollbackClusterType: RollbackClusterTypes;
  }

  interface Emits {
    (e: 'add', index: number, appendList: Array<IDataRow>): void;
    (e: 'remove', index: number): void;
    (e: 'batchEdit', obj: Record<string, any>): void;
    (e: 'showSelector'): void;
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const rollbackRenderDataInfo = {
    [RollbackClusterTypes.BUILD_INTO_NEW_CLUSTER]: {
      RenderData: NewCluster,
      RenderDataRow: NewClusterRow,
    },
    [RollbackClusterTypes.BUILD_INTO_EXIST_CLUSTER]: {
      RenderData: ExistCluster,
      RenderDataRow: ExistClusterRow,
    },
    [RollbackClusterTypes.BUILD_INTO_METACLUSTER]: {
      RenderData: OriginCluster,
      RenderDataRow: OriginClusterRow,
    },
  };

  const rowRefs = ref();
  const tableData = computed(() => props.data);
  const components = computed(() => rollbackRenderDataInfo[props.rollbackClusterType]);

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
    },
  });
</script>
