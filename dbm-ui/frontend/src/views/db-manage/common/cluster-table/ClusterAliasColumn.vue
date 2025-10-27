<template>
  <TableColumn
    class-name="cluster-table-alias-column"
    col-key="name"
    :filter="columnFilter?.['name']"
    :min-width="150"
    :title="t('集群名称/别名')">
    <template #default="{ row }: { row: IRowData }">
      <div>{{ row.cluster_name || '--' }}</div>
      <TextOverflowLayout>
        {{ row.cluster_alias || '--' }}
        <template
          v-if="!row.isOffline"
          #append>
          <UpdateClusterAliasName
            :data="row"
            @success="handleUpdateSuccess" />
        </template>
      </TextOverflowLayout>
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { useClusterColumnFilter } from '@hooks';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import UpdateClusterAliasName from '@views/db-manage/common/UpdateClusterAliasName.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    clusterType: ISupportClusterType;
  }

  export type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  type IRowData = ClusterModel<T>;

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_type: props.clusterType,
  });

  const handleUpdateSuccess = () => {
    emits('refresh');
  };
</script>
