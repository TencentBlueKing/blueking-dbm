<template>
  <TableColumn
    col-key="cluster_ids"
    :filter="columnFilter?.['cluster_ids']"
    fixed="left"
    title="ID"
    :width="80">
    <template #default="{ row }: { row: IRowData }">
      {{ row.id }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useClusterColumnFilter } from '@hooks';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  const props = defineProps<Props>();

  type IRowData = ClusterModel<T>;

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_type: props.clusterType,
  });
</script>
