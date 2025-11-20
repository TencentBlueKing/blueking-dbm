<template>
  <InfoList>
    <InfoItem :label="t('集群别名')">
      {{ data.cluster_alias || '--' }}
      <UpdateClusterAliasName
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
    <InfoItem :label="masterDomainLabel">
      {{ data.masterDomainDisplayName }}
    </InfoItem>
    <slot name="clbMaster" />
    <slot name="polaris" />
    <InfoItem
      v-if="slots.slaveDomain"
      :label="t('从访问入口')">
      <slot name="slaveDomain" />
    </InfoItem>
    <slot name="clbSlave" />
    <InfoItem :label="t('标签')">
      <ClusterTag
        :data="data"
        @success="handleSuccess" />
    </InfoItem>
    <InfoItem
      v-if="slots.load"
      :label="t('负载')">
      <slot name="load" />
    </InfoItem>
    <InfoItem :label="t('容量使用率')">
      <ClusterStatsCell
        :cluster-id="data.id"
        :cluster-type="clusterType" />
    </InfoItem>
    <InfoItem
      v-if="slots.clusterTypeName"
      :label="t('架构版本')">
      <slot name="clusterTypeName" />
    </InfoItem>
    <InfoItem
      v-if="slots.syncMode"
      :label="t('同步模式')">
      <slot name="syncMode" />
    </InfoItem>
    <slot name="moduleName" />
    <InfoItem
      v-if="slots.moduleNames"
      label="Modules">
      <slot name="moduleNames" />
    </InfoItem>
    <CommonInfo :data="data" />
  </InfoList>
</template>

<script lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ClusterTag from '@components/cluster-tag/index.vue';

  import ClusterStatsCell from '@views/db-manage/common/cluster-stats-cell/Index.vue';
  import UpdateClusterAliasName from '@views/db-manage/common/UpdateClusterAliasName.vue';

  import ClbInfo from './ClbInfo.vue';
  import CommonInfo from './CommonInfo.vue';
  import InfoList, { InfoItem } from './components/Index.vue';
  import ModuleNameInfo from './ModuleNameInfo.vue';
  import PolarisInfo from './PolarisInfo.vue';
  import type { ClusterDetailModel, ISupportClusterType } from './types';

  export { ClbInfo, InfoItem, InfoList, ModuleNameInfo, PolarisInfo };
</script>
<script setup lang="ts" generic="T extends ISupportClusterType">
  export interface Props<C extends ISupportClusterType> {
    clusterType: C;
    data: ClusterDetailModel<C>;
  }

  export type Emits = (e: 'refresh') => void;

  export interface Slots {
    clbMaster: () => VNode;
    clbSlave: () => VNode;
    clusterTypeName: () => VNode;
    load: () => VNode;
    moduleName: () => VNode;
    moduleNames: () => VNode;
    polaris: () => VNode;
    slaveDomain: () => VNode;
    syncMode: () => VNode;
  }

  defineProps<Props<T>>();
  const emits = defineEmits<Emits>();
  const slots = defineSlots<Slots>();

  const { t } = useI18n();

  const masterDomainLabel = computed(() => {
    if (slots.slaveDomain && slots.slaveDomain()) {
      return t('主访问入口');
    }
    return t('访问入口');
  });

  const handleSuccess = () => {
    emits('refresh');
  };
</script>
