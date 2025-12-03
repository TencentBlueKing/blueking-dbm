<template>
  <TableColumn
    class-name="instance-table-instance-address-column"
    col-key="instance_address"
    fixed="left"
    :min-width="columnMinWidth"
    :title="t('实例')">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'instance_address',
            label: t('实例'),
          },
          {
            field: 'ip',
            label: 'IP',
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('实例') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: IRowData }">
      <InstanceAddressCell
        :cluster-type="clusterType"
        :data="row"
        :db-type="dbType">
        <template #append>
          <slot
            name="append"
            v-bind="{ data: row }" />
        </template>
      </InstanceAddressCell>
    </template>
  </TableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import InstanceAddressCell from './components/InstanceAddressCell.vue';
  import useColumnCopy from './hooks/useColumnCopy';
  import type { Expose as InstanceTableExpose } from './Index.vue';
  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    dbType?: DBTypes;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceTableExpose | null;
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

  const columnMinWidth = window.innerWidth < 1366 ? 150 : 200;

  const { handleCopyAll, handleCopySelected } = useColumnCopy(props);
</script>
<style lang="less">
  .instance-table-instance-address-column {
    &:hover,
    .is-hover {
      [class*='db-icon'] {
        display: inline !important;
      }
    }

    [class*='db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
