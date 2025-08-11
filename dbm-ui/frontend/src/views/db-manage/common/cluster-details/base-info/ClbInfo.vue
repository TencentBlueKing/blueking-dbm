<template>
  <InfoItem
    v-if="clbEntry && clbEntry.target_details[0]"
    :label="label">
    {{ clbEntry.target_details[0]?.clb_ip }}
    <span>,</span>
    {{ clbEntry.target_details[0]?.clb_domain }}
  </InfoItem>
</template>
<script
  setup
  lang="ts"
  generic="
    T extends
      | ClusterTypes.ES
      | ClusterTypes.MONGO_SHARED_CLUSTER
      | ClusterTypes.TENDBHA
      | ClusterTypes.REDIS
      | ClusterTypes.TENDBCLUSTER
  ">
  import ClusterEntryDetailModel, { type ClbTargetDetails } from '@services/model/cluster-entry/cluster-entry-details';

  import { ClusterTypes } from '@common/const';

  import { InfoItem } from './components/Index.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: C;
    data: ClusterDetailModel<C>;
    label?: string;
    role?: string;
  }

  const props = withDefaults(defineProps<Props<T>>(), {
    label: 'CLB',
    role: undefined,
  });

  const clbEntry = computed(() =>
    (props.data.cluster_entry_details as ClusterEntryDetailModel<ClbTargetDetails>[]).find((item) => {
      if (props.role) {
        // 多个clb的情况下用role进一步区分
        return item.cluster_entry_type === 'clb' && item.role === props.role;
      } else {
        return item.cluster_entry_type === 'clb';
      }
    }),
  );
</script>
