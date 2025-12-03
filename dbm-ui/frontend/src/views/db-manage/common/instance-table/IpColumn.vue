<template>
  <TableColumn
    class-name="instance-table-ip-column"
    col-key="ip"
    :filter="columnFilter?.['ip']"
    :title="t('主机 IP')"
    :width="140">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'ip',
            label: 'IP',
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('主机 IP') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: IRowData }">
      <IpCell
        :cluster-type="clusterType"
        :data="row">
      </IpCell>
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { useInstanceColumnFilter } from '@hooks';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import IpCell from './components/IpCell.vue';
  import useColumnCopy from './hooks/useColumnCopy';
  import type { Expose as ClusterTableExpose } from './Index.vue';
  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => ClusterTableExpose | null;
    isFilter: boolean;
    selectedList: InstanceModel<clusterType>[];
  }

  type IRowData = InstanceModel<T>;

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_type: props.clusterType,
  });
  const { handleCopyAll, handleCopySelected } = useColumnCopy(props);
</script>
