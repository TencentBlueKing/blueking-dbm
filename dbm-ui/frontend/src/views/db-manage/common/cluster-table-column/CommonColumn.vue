<template>
  <BkTableColumn
    field="major_version"
    :filter="{
      list: columnAttrs.major_version,
      checked: columnCheckedMap.major_version,
    }"
    :label="t('版本')"
    :min-width="100">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.major_version || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="disaster_tolerance_level"
    :label="t('容灾要求')"
    :min-width="100">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.disasterToleranceLevelName || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="region"
    :filter="{
      list: columnAttrs.region,
      checked: columnCheckedMap.region,
    }"
    :label="t('地域')"
    :min-width="100">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.region || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="spec_name"
    :label="t('规格')"
    :min-width="180">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.cluster_spec.spec_name || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="bk_cloud_id"
    :filter="{
      list: columnAttrs.bk_cloud_id,
      checked: columnCheckedMap.bk_cloud_id,
    }"
    :label="t('管控区域')"
    :width="120">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.bk_cloud_name ? `${data.bk_cloud_name}[${data.bk_cloud_id}]` : '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="creator"
    :label="t('创建人')"
    :width="140">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.creator || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="create_at"
    :label="t('部署时间')"
    sort
    :width="250">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.createAtDisplay || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="cluster_time_zone"
    :filter="{
      list: columnAttrs.time_zone,
      checked: columnCheckedMap.time_zone,
    }"
    :label="t('时区')"
    :width="100">
    <template #default="{ data }: { data: TendnclusterModel }">
      {{ data.cluster_time_zone || '--' }}
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendnclusterModel from '@services/model/tendbcluster/tendbcluster';

  import { useLinkQueryColumnSerach } from '@hooks';

  import type { ISupportClusterType } from './types';

  interface Props {
    clusterType: ISupportClusterType;
  }

  interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { columnAttrs, columnCheckedMap } = useLinkQueryColumnSerach({
    searchType: props.clusterType,
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    fetchDataFn: () => handleRefresh(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    },
  });

  const handleRefresh = () => {
    emits('refresh');
  };
</script>
