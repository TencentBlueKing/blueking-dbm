<template>
  <TableColumn
    class-name="cluster-table-alias-column"
    col-key="cluster_alias"
    :min-width="150"
    :title="t('别名')">
    <template #default="{ row }: { row: IRowData }">
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

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import UpdateClusterAliasName from '@views/db-manage/common/UpdateClusterAliasName.vue';

  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: ISupportClusterType;
  }

  export type Emits = (e: 'refresh') => void;

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  type IRowData = ClusterModel<T>;

  const handleUpdateSuccess = () => {
    emits('refresh');
  };
</script>
