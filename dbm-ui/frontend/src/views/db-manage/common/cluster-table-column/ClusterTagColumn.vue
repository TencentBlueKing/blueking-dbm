<template>
  <BkTableColumn
    field="tag"
    :label="t('标签')"
    :width="200">
    <template #default="{ data }: { data: IRowData }">
      <ClusterTagCell
        :data="data"
        @success="handleOperateSuccess" />
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import ClusterTagCell from './components/cluster-tag-cell/Index.vue';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  type Emits = (e: 'success') => void;

  type IRowData = ClusterModel<T>;

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleOperateSuccess = () => {
    emits('success');
  };
</script>
