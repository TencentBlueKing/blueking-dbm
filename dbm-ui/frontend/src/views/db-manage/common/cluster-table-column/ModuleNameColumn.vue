<template>
  <BkTableColumn
    field="db_module_name"
    :label="t('模块')"
    :width="150">
    <template #default="{ data }: { data: IRowData }">
      {{ data.db_module_name || '--' }}
    </template>
  </BkTableColumn>
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
