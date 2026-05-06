<template>
  <TableColumn
    class-name="instance-table-master-domain-column"
    col-key="master_domain"
    :min-width="columnMinWidth"
    :title="labelDisplay">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'master_domain',
            label: labelDisplay,
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ labelDisplay }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: IRowData }">
      <MasterDomainCell
        :cluster-type="clusterType"
        :data="row"
        :db-type="dbType">
        <template #append>
          <slot
            name="append"
            v-bind="{ data: row }" />
        </template>
      </MasterDomainCell>
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import MasterDomainCell from './components/MasterDomainCell.vue';
  import useColumnCopy from './hooks/useColumnCopy';
  import type { Expose as ClusterTableExpose } from './Index.vue';
  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    dbType?: DBTypes;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => ClusterTableExpose | null;
    isFilter: boolean;
    label?: string;
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

  const labelDisplay = computed(() => (props.label ? props.label : t('所属集群')));
</script>
