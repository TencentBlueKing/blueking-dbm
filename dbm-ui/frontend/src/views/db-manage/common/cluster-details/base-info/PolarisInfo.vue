<template>
  <InfoItem
    v-if="polarisEntry && polarisEntry.target_details[0]"
    :label="t('北极星')">
    {{ polarisEntry.target_details[0]?.polaris_l5 }}
    <span>,</span>
    {{ polarisEntry.target_details[0]?.polaris_name }}
    <a
      v-if="polarisEntry.target_details[0].url"
      target="_blank"
      :url="polarisEntry.target_details[0].url">
      <DbIcon type="link" />
    </a>
  </InfoItem>
</template>
<script setup lang="ts" generic="T extends ClusterTypes.ES | ClusterTypes.REDIS">
  import { useI18n } from 'vue-i18n';

  import ClusterEntryDetailModel, {
    type ClbPolarisTargetDetails,
  } from '@services/model/cluster-entry/cluster-entry-details';

  import { ClusterTypes } from '@common/const';

  import { InfoItem } from './components/Index.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: C;
    data: ClusterDetailModel<C>;
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const polarisEntry = computed(() =>
    (props.data.cluster_entry_details as ClusterEntryDetailModel<ClbPolarisTargetDetails>[]).find(
      (item) => item.cluster_entry_type === 'polaris',
    ),
  );
</script>
