<template>
  <InfoItem
    class="cluster-details-k8s-spec"
    :label="t('规格')"
    style="flex: 1 1 100%">
    <div
      v-if="isLoading"
      class="rotate-loading"
      style="display: inline-block">
      <DbIcon
        svg
        type="sync-pending" />
    </div>
    <template v-else>
      <BkTag
        v-for="item in specData?.spec.componentList"
        :key="item.componentName">
        <span class="text-bold">{{
          item.componentName.charAt(0).toUpperCase() + item.componentName.slice(1).toLowerCase()
        }}</span>
        ×
        <span class="text-bold">{{ item.replicas }}</span>
        （
        <span>{{ item.limit.cpu }}</span>
        /
        <span>{{ item.limit.memory }}</span>
        ）
      </BkTag>
    </template>
  </InfoItem>
</template>
<script
  setup
  lang="ts"
  generic="T extends ClusterTypes.K8S_SURREALDB_HA | ClusterTypes.K8S_SURREALDB_SINGLE | ClusterTypes.K8S_QDRANT_HA">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getQdrantHaComponentSpec } from '@services/source/qdrantHa';
  import { getSurrealdbHaComponentSpec } from '@services/source/surrealdbHa';
  import { getSurrealdbSingleComponentSpec } from '@services/source/surrealdbSingle';

  import { ClusterTypes } from '@common/const';

  import { InfoItem } from './components/Index.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    clusterType: C;
    data: ClusterDetailModel<C>;
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const requestApiMap = {
    [ClusterTypes.K8S_QDRANT_HA]: getQdrantHaComponentSpec,
    [ClusterTypes.K8S_SURREALDB_HA]: getSurrealdbHaComponentSpec,
    [ClusterTypes.K8S_SURREALDB_SINGLE]: getSurrealdbSingleComponentSpec,
  };

  const { data: specData, loading: isLoading } = useRequest(
    requestApiMap[props.clusterType as keyof typeof requestApiMap],
    {
      defaultParams: [
        {
          clusterName: props.data.cluster_name,
          k8sClusterName: props.data.k8s_cluster_name,
          namespace: props.data.namespace,
        },
      ],
    },
  );
</script>

<style lang="less">
  .cluster-details-k8s-spec {
    .text-bold {
      font-weight: bolder;
    }
  }
</style>
