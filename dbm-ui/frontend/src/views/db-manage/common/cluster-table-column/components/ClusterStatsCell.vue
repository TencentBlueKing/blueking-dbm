<template>
  <div
    v-if="isLoading"
    class="rotate-loading"
    style="display: inline-block">
    <DbIcon
      svg
      type="sync-pending" />
  </div>
  <template v-else>
    <ClusterCapacityUsageRate
      v-if="clusterStatInfo && clusterStatInfo[clusterId]"
      :cluster-stats="clusterStatInfo[clusterId]" />
    <span v-else>--</span>
  </template>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { queryClusterStat } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue';

  import type { ISupportClusterType } from '../types';

  interface Props {
    clusterType: ISupportClusterType;
    clusterId: number;
  }

  const props = defineProps<Props>();

  const route = useRoute();

  const { loading: isLoading, data: clusterStatInfo } = useRequest(
    (params) =>
      queryClusterStat(params, {
        cache: route.name as string,
      }),
    {
      defaultParams: [
        {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_type:
            props.clusterType === ClusterTypes.REDIS
              ? [
                  ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                  ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                  ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                  ClusterTypes.PREDIXY_REDIS_CLUSTER,
                ].join(',')
              : props.clusterType,
        },
      ],
    },
  );
</script>
