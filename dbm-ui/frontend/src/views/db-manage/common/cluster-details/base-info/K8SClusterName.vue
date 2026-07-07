<template>
  <InfoItem :label="t('BCS 集群')">
    {{ data.k8s_cluster_name || '--' }}
  </InfoItem>
</template>
<script
  setup
  lang="ts"
  generic="T extends ClusterTypes.K8S_SURREALDB_HA | ClusterTypes.K8S_SURREALDB_SINGLE | ClusterTypes.K8S_QDRANT_HA">
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
