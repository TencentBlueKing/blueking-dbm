<template>
  <BaseInfo>
    <InfoItem :label="t('集群别名')">
      {{ data.cluster_alias || '--' }}
      <UpdateClusterAliasName
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
    <InfoItem :label="t('主访问入口')">
      {{ data.masterDomainDisplayName }}
    </InfoItem>
    <InfoItem :label="t('从访问入口')">
      <SlaveDomain
        :cluster-type="ClusterTypes.TENDBCLUSTER"
        :data="data.slaveEntryList" />
    </InfoItem>
    <InfoItem
      v-if="clbMasterEntry && clbMasterEntry.target_details[0]"
      label="CLB（Master）">
      {{ clbMasterEntry.target_details[0]?.clb_ip }}
      <span>,</span>
      {{ clbMasterEntry.target_details[0]?.clb_domain }}
    </InfoItem>
    <InfoItem
      v-if="clbSlaveEntry && clbSlaveEntry.target_details[0]"
      label="CLB（Slave）">
      {{ clbSlaveEntry.target_details[0]?.clb_ip }}
      <span>,</span>
      {{ clbSlaveEntry.target_details[0]?.clb_domain }}
    </InfoItem>
    <InfoItem :label="t('标签')">
      <ClusterTag
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
    <InfoItem :label="t('容量使用率')">
      <ClusterStatsCell
        :cluster-id="data.id"
        :cluster-type="ClusterTypes.TENDBCLUSTER" />
    </InfoItem>
    <InfoItem :label="t('模块')">
      {{ data.db_module_name || '--' }}
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

  import ClusterEntryDetailModel, { type ClbTargetDetails } from '@services/model/cluster-entry/cluster-entry-details';
  import TendbClusterDetailModel from '@services/model/tendbcluster/tendbcluster-detail';

  import { ClusterTypes } from '@common/const';

  import ClusterTag from '@components/cluster-tag/index.vue';

  import BaseInfo, { InfoItem } from '@views/db-manage/common/cluster-details/base-info/Index.vue';
  import SlaveDomain from '@views/db-manage/common/cluster-details/SlaveDomain.vue';
  import ClusterStatsCell from '@views/db-manage/common/cluster-stats-cell/Index.vue';
  import UpdateClusterAliasName from '@views/db-manage/common/UpdateClusterAliasName.vue';

  interface Props {
    data: TendbClusterDetailModel;
  }

  export type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clbMasterEntry = computed(() =>
    (props.data.cluster_entry_details as ClusterEntryDetailModel<ClbTargetDetails>[]).find(
      (item) => item.cluster_entry_type === 'clb' && item.role === 'master_entry',
    ),
  );

  const clbSlaveEntry = computed(() =>
    (props.data.cluster_entry_details as ClusterEntryDetailModel<ClbTargetDetails>[]).find(
      (item) => item.cluster_entry_type === 'clb' && item.role === 'slave_entry',
    ),
  );

  const handleSuccess = () => {
    emits('refresh');
  };
</script>
