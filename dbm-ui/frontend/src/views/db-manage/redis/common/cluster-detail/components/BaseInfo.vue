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
    <InfoItem
      v-if="clbEntry && clbEntry.target_details[0]"
      label="CLB">
      {{ clbEntry.target_details[0]?.clb_ip }}
      <span>,</span>
      {{ clbEntry.target_details[0]?.clb_domain }}
    </InfoItem>
    <InfoItem :label="t('标签')">
      <ClusterTag
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
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
    <InfoItem :label="t('容量使用率')">
      <ClusterStatsCell
        :cluster-id="data.id"
        :cluster-type="ClusterTypes.REDIS" />
    </InfoItem>
    <InfoItem :label="t('架构版本')">
      {{ data.cluster_type_name || '--' }}
    </InfoItem>
    <InfoItem label="Modules">
      <TagBlock :data="data.module_names" />
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
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ClusterEntryDetailModel, {
    type ClbPolarisTargetDetails,
    type ClbTargetDetails,
  } from '@services/model/cluster-entry/cluster-entry-details';
  import RedisDetailModel from '@services/model/redis/redis-detail';

  import { ClusterTypes } from '@common/const';

  import ClusterTag from '@components/cluster-tag/index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import BaseInfo, { InfoItem } from '@views/db-manage/common/cluster-details/base-info/Index.vue';
  import ClusterStatsCell from '@views/db-manage/common/cluster-stats-cell/Index.vue';
  import UpdateClusterAliasName from '@views/db-manage/common/UpdateClusterAliasName.vue';

  interface Props {
    data: RedisDetailModel;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();
  const { t } = useI18n();
  export type Emits = (e: 'refresh') => void;

  const clbEntry = computed(() =>
    (props.data.cluster_entry_details as ClusterEntryDetailModel<ClbTargetDetails>[]).find(
      (item) => item.cluster_entry_type === 'clb',
    ),
  );
  const polarisEntry = computed(() =>
    (props.data.cluster_entry_details as ClusterEntryDetailModel<ClbPolarisTargetDetails>[]).find(
      (item) => item.cluster_entry_type === 'polaris',
    ),
  );

  const handleSuccess = () => {
    emits('refresh');
  };
</script>
