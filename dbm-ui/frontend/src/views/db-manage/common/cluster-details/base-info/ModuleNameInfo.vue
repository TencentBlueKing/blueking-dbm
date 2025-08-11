<template>
  <InfoItem :label="t('模块')">
    {{ data.db_module_name || '--' }}
  </InfoItem>
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

  import { InfoItem } from './components/Index.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: C;
    data: ClusterDetailModel<C>;
  }

  defineProps<Props<T>>();

  const { t } = useI18n();
</script>
