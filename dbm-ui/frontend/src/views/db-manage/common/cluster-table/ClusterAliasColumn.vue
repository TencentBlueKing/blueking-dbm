<template>
  <BkTableColumn
    class-name="cluster-table-alias-column"
    field="cluster_alias"
    :label="t('别名')"
    :min-width="150">
    <template #default="{ data }: { data: IRowData }">
      <TextOverflowLayout>
        {{ data.cluster_alias || '--' }}
        <template
          v-if="!data.isOffline"
          #append>
          <UpdateClusterAliasName
            :data="data"
            @success="handleUpdateSuccess" />
        </template>
      </TextOverflowLayout>
    </template>
  </BkTableColumn>
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
<style lang="less">
  tr.vxe-body--row {
    &:hover {
      .cluster-table-alias-column {
        .cluster-alias-name-edit-btn {
          display: inline-block;
        }
      }
    }
  }

  .cluster-table-alias-column {
    .cluster-alias-name-edit-btn {
      display: none;
    }
  }
</style>
