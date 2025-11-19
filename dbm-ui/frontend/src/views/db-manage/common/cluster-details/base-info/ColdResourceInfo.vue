<template>
  <InfoItem :label="t('低频存储')">
    {{ coldResourceDisplay }}
  </InfoItem>
</template>
<script setup lang="ts" generic="T extends ClusterTypes.DORIS">
  import { useI18n } from 'vue-i18n';

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

  const coldResourceDisplay = computed(() => {
    const { id, name, region, used } = props.data.cold_resource;
    if (id) {
      return `${name} （${t('已使用：')}${used} G , ${t('地域：')}${region}）`;
    }
    return '--';
  });
</script>
