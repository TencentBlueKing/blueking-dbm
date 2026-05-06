<template>
  <TableColumn
    col-key="id"
    :filter="columnFilter?.['id']"
    title="ID"
    :width="80">
    <template #default="{ row }: { row: IRowData }">
      {{ row.id }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useInstanceColumnFilter } from '@hooks';

  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  const props = defineProps<Props>();

  type IRowData = InstanceModel<T>;

  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_type: props.clusterType,
  });
</script>
