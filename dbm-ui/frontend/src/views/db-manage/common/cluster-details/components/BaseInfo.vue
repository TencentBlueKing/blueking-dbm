<template>
  <BaseInfo>
    <InfoItem :label="t('集群别名')">
      {{ data.cluster_alias || '--' }}
    </InfoItem>
    <InfoItem :label="t('容量使用率')"> -- </InfoItem>
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
  </BaseInfo>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import BaseInfo, { InfoItem } from '../base-info/Index.vue';

  interface Props {
    data: Pick<
      TendbhaModel,
      | 'cluster_alias'
      | 'id'
      | 'cluster_name'
      | 'major_version'
      | 'disasterToleranceLevelName'
      | 'region'
      | 'cluster_spec'
      | 'bk_cloud_name'
      | 'bk_cloud_id'
      | 'bk_biz_name'
      | 'cluster_subzons'
      | 'creator'
      | 'createAtDisplay'
      | 'cluster_time_zone'
      | 'status'
      | 'cluster_type'
    >;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
