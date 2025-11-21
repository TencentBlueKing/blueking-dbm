<template>
  <TableColumn
    col-key="db_module_name"
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

  import { ClusterTypes } from '@common/const';

  import type { ClusterModel } from './types';

  export interface Props<T> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: T;
  }

  type IRowData = ClusterModel<T>;

  defineProps<Props<T>>();

  const { t } = useI18n();
</script>
