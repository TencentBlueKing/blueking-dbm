<template>
  <TableColumn
    col-key="db_module_id"
    :filter="columnFilter?.db_module_id"
    :title="t('模块')"
    :width="150">
    <template #default="{ row }: { row: IRowData }">
      {{ row.db_module_name || '--' }}
    </template>
  </TableColumn>
</template>
<script
  setup
  lang="ts"
  generic="
    T extends
      | ClusterTypes.TENDBCLUSTER
      | ClusterTypes.TENDBHA
      | ClusterTypes.TENDBSINGLE
      | ClusterTypes.SQLSERVER_HA
      | ClusterTypes.SQLSERVER_SINGLE
      | ClusterTypes.RIAK
  ">
  import { useI18n } from 'vue-i18n';

  import { useClusterColumnFilter } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import type { ClusterModel } from './types';

  export interface Props<T> {
    clusterType: T;
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_attrs: ['db_module_id'] as const,
    cluster_type: props.clusterType,
  });
</script>
