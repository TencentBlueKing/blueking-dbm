<template>
  <BaseInfo>
    <InfoItem :label="t('集群别名')">
      {{ data.cluster_alias || '--' }}
      <UpdateClusterAliasName
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
    <InfoItem :label="t('访问入口')">
      {{ data.masterDomainDisplayName }}
    </InfoItem>
    <InfoItem :label="t('标签')">
      <ClusterTag
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
    <InfoItem :label="t('容量使用率')">
      <ClusterStatsCell
        :cluster-id="data.id"
        :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER" />
    </InfoItem>
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

  import MongodbModel from '@services/model/mongodb/mongodb';

  import { ClusterTypes } from '@common/const';

  import ClusterTag from '@components/cluster-tag/index.vue';

  import BaseInfo, { InfoItem } from '@views/db-manage/common/cluster-details/base-info/Index.vue';
  import ClusterStatsCell from '@views/db-manage/common/cluster-stats-cell/Index.vue';
  import UpdateClusterAliasName from '@views/db-manage/common/UpdateClusterAliasName.vue';

  interface Props {
    data: MongodbModel;
  }

  export type Emits = (e: 'refresh') => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleSuccess = () => {
    emits('refresh');
  };
</script>
