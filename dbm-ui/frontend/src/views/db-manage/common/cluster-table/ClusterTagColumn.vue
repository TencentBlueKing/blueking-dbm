<template>
  <BkTableColumn
    field="tag"
    :label="t('标签')"
    :width="200">
    <template #default="{ data }: { data: IRowData }">
      <ClusterTag
        :data="data"
        mode="vertical"
        @success="handleOperateSuccess" />
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import ClusterTag from '@components/cluster-tag/index.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: ISupportClusterType;
  }

  type Emits = (e: 'refresh') => void;

  type IRowData = ClusterModel<T>;

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleOperateSuccess = () => {
    emits('refresh');
  };
</script>
