<template>
  <BaseInfo>
    <InfoItem :label="t('集群名称')">
      {{ data.cluster_name }}
    </InfoItem>
    <InfoItem :label="t('主访问入口')">
      {{ data.master_domain }}
    </InfoItem>
    <InfoItem :label="t('从访问入口')">
      {{ data.slave_domain }}
    </InfoItem>
    <InfoItem :label="t('所属 DB 模块')">
      {{ data.db_module_name }}
    </InfoItem>
    <InfoItem :label="t('创建人')">
      {{ data.creator }}
    </InfoItem>
    <InfoItem :label="t('管控区域')">
      {{ data.bk_cloud_name ? `${data.bk_cloud_name}[${data.bk_cloud_id}]` : '--' }}
    </InfoItem>
    <InfoItem :label="t('创建时间')">
      {{ data.createAtDisplay }}
    </InfoItem>
    <InfoItem :label="t('容灾要求')">
      {{ data.disasterToleranceLevelName }}
    </InfoItem>
    <InfoItem :label="t('规格')">
      {{ data.cluster_spec.spec_name || '--' }}
    </InfoItem>
  </BaseInfo>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import BaseInfo, { InfoItem } from '@views/db-manage/common/cluster-details/base-info/Index.vue';

  interface Props {
    data: TendbhaModel;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
