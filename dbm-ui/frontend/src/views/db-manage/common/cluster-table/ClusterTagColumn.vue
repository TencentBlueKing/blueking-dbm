<template>
  <TableColumn
    col-key="tag"
    :filter="columnFilter?.['tag']"
    :title="t('标签')"
    :width="200">
    <template #default="{ row }: { row: IRowData }">
      <ClusterTag
        :data="row"
        mode="vertical"
        @success="handleOperateSuccess" />
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { useClusterColumnFilter } from '@hooks';

  import ClusterTag from '@components/cluster-tag/index.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  type Emits = (e: 'refresh') => void;

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_type: props.clusterType,
  });

  const handleOperateSuccess = () => {
    emits('refresh');
  };
</script>
