<template>
  <TableColumn
    col-key="mongodb_state"
    :filter="columnFilter?.['mongodb_state']"
    :title="t('副本集状态')"
    :width="150">
    <template #default="{ row }: { row: IRowData }">
      {{ row.mongodb_state || '--' }}
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
    instance_attrs: ['mongodb_state'] as const,
  });
</script>
