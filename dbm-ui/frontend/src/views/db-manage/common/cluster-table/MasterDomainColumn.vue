<template>
  <BkTableColumn
    class-name="cluster-table-master-domain-column"
    :field="field"
    fixed="left"
    :label="label"
    :min-width="columnMinWidth"
    visiable>
    <template #header>
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
    <template #default="{ data }: { data: IRowData }">
      <MasterDomainCell
        :cluster-type="clusterType"
        :data="data"
        :db-type="dbType"
        @go-detail="handleToDetails"
        @refresh="handleRefresh">
        <template #append>
          <slot
            name="append"
            v-bind="{ data }" />
        </template>
      </MasterDomainCell>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import MasterDomainCell from './components/MasterDomainCell.vue';
  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    dbType?: DBTypes;
    field: string;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
    isFilter: boolean;
    label: string;
    selectedList: ClusterModel<clusterType>[];
  }

  export interface Emits {
    (e: 'go-detail', params: number, event: MouseEvent): void;
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

  const handleToDetails = (id: number, event: MouseEvent) => {
    emits('go-detail', id, event);
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
