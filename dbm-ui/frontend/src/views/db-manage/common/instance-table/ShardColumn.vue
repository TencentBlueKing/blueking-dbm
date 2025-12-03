<template>
  <TableColumn
    col-key="shard"
    :filter="columnFilter?.['shard']"
    :title="t('分片名')"
    :width="150">
    <template #default="{ row }: { row: IRowData }">
      {{ row.shard || '--' }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ClusterTypes.MONGO_SHARED_CLUSTER | ClusterTypes.MONGO_REPLICA_SET">
  import { useI18n } from 'vue-i18n';

  import { useInstanceColumnFilter } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import type { InstanceModel } from './types';

  export interface Props<T> {
    clusterType: T;
  }

  type IRowData = InstanceModel<T>;

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_type: props.clusterType,
  });
</script>
