<template>
  <InfoItem :label="t('版本')">
    {{ data.major_version || '--' }}
  </InfoItem>
  <InfoItem :label="t('容灾要求')">
    {{ data.disasterToleranceLevelName }}
  </InfoItem>
  <InfoItem :label="t('地域')">
    <div>{{ data.region || '--' }}</div>
  </InfoItem>
  <InfoItem :label="t('园区')">
    <div>{{ data.cluster_subzons.join('，') || '--' }}</div>
  </InfoItem>
  <InfoItem :label="t('规格')">
    {{ data.cluster_spec.spec_name || '--' }}
  </InfoItem>
  <InfoItem :label="t('管控区域')">
    {{ data.bk_cloud_name ? `${data.bk_cloud_name}[${data.bk_cloud_id}]` : '--' }}
  </InfoItem>
  <InfoItem :label="t('创建人')">
    {{ data.creator }}
  </InfoItem>
  <InfoItem :label="t('部署时间')">
    {{ data.createAtDisplay }}
  </InfoItem>
  <InfoItem :label="t('时区')">
    {{ data.cluster_time_zone || '--' }}
  </InfoItem>
</template>

<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { InfoItem } from './components/Index.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    data: ClusterDetailModel<C>;
  }

  defineProps<Props<T>>();

  const { t } = useI18n();
</script>
