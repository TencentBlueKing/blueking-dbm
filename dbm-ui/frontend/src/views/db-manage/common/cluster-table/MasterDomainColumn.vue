<template>
  <TableColumn
    class-name="cluster-table-master-domain-column"
    col-key="master_domain"
    fixed="left"
    :min-width="columnMinWidth"
    :title="label">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'masterDomain',
            label: t('域名'),
          },
          {
            field: 'masterDomainDisplayName',
            label: t('域名:端口'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ label }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: IRowData }">
      <MasterDomainCell
        :cluster-type="clusterType"
        :data="row"
        :db-type="dbType"
        @go-detail="handleToDetails"
        @refresh="handleRefresh">
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
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    dbType?: DBTypes;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => ClusterTableExpose | null;
    isFilter: boolean;
    label: string;
    selectedList: ClusterModel<clusterType>[];
  }

  export interface Emits {
    (e: 'go-detail', params: number, event: MouseEvent, detailPanel?: string): void;
    (e: 'refresh'): void;
  }

  export interface Slots<T extends ISupportClusterType> {
    append?: (params: { data: ClusterModel<T> }) => VNode;
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();
  defineSlots<Slots<T>>();

  const { t } = useI18n();

  const columnMinWidth = window.innerWidth < 1366 ? 180 : 280;

  const { handleCopyAll, handleCopySelected } = useColumnCopy(props);

  const handleToDetails = (id: number, event: MouseEvent, detailPanel?: string) => {
    emits('go-detail', id, event, detailPanel);
  };

  const handleRefresh = () => {
    emits('refresh');
  };
</script>
<style lang="less">
  .cluster-table-master-domain-column {
    &:hover,
    .is-hover {
      [class*='db-icon'] {
        display: inline !important;
      }

      .master-domain-alarm-sign {
        display: flex;
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
