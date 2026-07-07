<template>
  <InfoItem :label="t('版本')">
    {{ data.major_version || '--' }}
  </InfoItem>
  <InfoItem
    v-if="!data.cluster_type.includes('k8s')"
    :label="t('容灾要求')">
    {{ data.disasterToleranceLevelName }}
  </InfoItem>
  <InfoItem :label="t('地域')">
    <div>{{ data.regionDisplay }}</div>
  </InfoItem>
  <InfoItem :label="t('园区')">
    <div>{{ data.clusterSubzonesDisplay }}</div>
  </InfoItem>
  <slot name="spec">
    <InfoItem :label="t('规格')">
      <MachineSpecCell
        mode="detail"
        :specs="data.machine_specs" />
    </InfoItem>
  </slot>
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
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MachineSpecCell from '@views/db-manage/common/cluster-details/components/machine-spec-cell/Index.vue';

  import { InfoItem } from './components/Index.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export interface Props<C extends ISupportClusterType> {
    data: ClusterDetailModel<C>;
  }

  export interface Slots {
    spec: () => VNode;
  }

  defineProps<Props<T>>();

  const { t } = useI18n();
</script>
