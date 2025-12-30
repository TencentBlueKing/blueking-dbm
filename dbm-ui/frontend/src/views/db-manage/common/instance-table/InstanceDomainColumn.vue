<template>
  <TableColumn
    class-name="instance-table-instance-domain-column"
    col-key="instance_domain"
    :min-width="columnMinWidth"
    :title="t('域名')">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'instance_domain',
            label: t('域名'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('域名') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: IRowData }">
      <InstanceDomainCell
        :cluster-type="clusterType"
        :data="row"
        :db-type="dbType">
        <template #append>
          <slot
            name="append"
            v-bind="{ data: row }" />
        </template>
      </InstanceDomainCell>
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ClusterTypes.MONGO_REPLICA_SET | ClusterTypes.MONGO_SHARED_CLUSTER">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes, DBTypes } from '@common/const';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import InstanceDomainCell from './components/InstanceDomainCell.vue';
  import useColumnCopy from './hooks/useColumnCopy';
  import type { Expose as ClusterTableExpose } from './Index.vue';
  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    dbType?: DBTypes;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => ClusterTableExpose | null;
    isFilter: boolean;
    selectedList: InstanceModel<clusterType>[];
  }

  export interface Slots<T extends ISupportClusterType> {
    append?: (params: { data: InstanceModel<T> }) => VNode;
  }

  type IRowData = InstanceModel<T>;

  const props = defineProps<Props<T>>();
  defineSlots<Slots<T>>();

  const { t } = useI18n();

  const columnMinWidth = window.innerWidth < 1366 ? 180 : 280;

  const { handleCopyAll, handleCopySelected } = useColumnCopy(props);
</script>
