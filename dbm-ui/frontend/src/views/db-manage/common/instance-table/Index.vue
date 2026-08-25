<template>
  <div ref="root">
    <DbTable
      ref="tableRef"
      v-bind="$attrs"
      :bk-ui-settings="bkUiSettings"
      class="db-instance-table"
      :data-source="dataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="filterValue"
      releate-url-query
      :row-class-name="getRowClass"
      row-key="id"
      selectable
      @bk-ui-settings-change="handleTableSettings"
      @filter-change="handleFilterChange"
      @request-success="handleRequestSuceess"
      @selection="handleSelection">
      <slot
        :key="tableRef?.loading"
        name="operation" />
      <slot name="instanceAddress" />
      <IdColumn :cluster-type="clusterType" />
      <slot name="domain" />
      <slot name="shard" />
      <CommonColumn :cluster-type="clusterType">
        <template #relatedCluster>
          <slot name="relatedCluster" />
        </template>
        <template #ip>
          <slot name="ip" />
        </template>
        <template #mongodbState>
          <slot name="mongodbState" />
        </template>
      </CommonColumn>
    </DbTable>
    <NewFeatureGuide
      v-if="isDataRequestSuccess"
      :list="newFeatureGuideList"
      name="instance_list" />
  </div>
</template>
<script lang="ts">
  import type { VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { ListBase } from '@services/types/listBase.ts';

  import DbTable from '@components/db-table/IndexNew.vue';

  import ClusterNameColumn from './ClusterNameColumn.vue';
  import CommonColumn from './CommonColumn.vue';
  import IdColumn from './IdColumn.vue';
  import InstanceAddressColumn from './InstanceAddressColumn.vue';
  import InstanceDomainColumn from './InstanceDomainColumn.vue';
  import IpColumn from './IpColumn.vue';
  import MasterDomainColumn from './MasterDomainColumn.vue';
  import MongodbStateColumn from './MongodbStateColumn.vue';
  import OperationColumn from './OperationColumn.vue';
  import ShardColumn from './ShardColumn.vue';

  export {
    ClusterNameColumn,
    IdColumn,
    InstanceAddressColumn,
    InstanceDomainColumn,
    IpColumn,
    MasterDomainColumn,
    MongodbStateColumn,
    OperationColumn,
    ShardColumn,
  };

  type IViewMode = 'drawer' | 'jump';
</script>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useUserProfile } from '@stores';

  import type { InstanceModel, ISupportClusterType } from './types.ts';

  export interface Props<C extends ISupportClusterType> {
    bkUiSettings?: ComponentProps<typeof DbTable>['bkUiSettings'];
    clusterType: C;
    dataSource: (params: any) => Promise<any>;
    disableSelectMethod?: (data: any) => boolean | string;
    filterValue?: Record<string, string>;
  }

  export interface Emits<C extends ISupportClusterType> {
    (e: 'selection', key: number[], list: InstanceModel<C>[]): void;
    (e: 'setting-change', params: NonNullable<Props<C>['bkUiSettings']>): void;
    (e: 'filter-change', params: Record<string, string>): void;
    (e: 'requestSuccess', value: ListBase<InstanceModel<C>[]>): void;
  }

  export interface Expose {
    // clearSelected: () => void;
    fetchData: (params: Record<string, any>) => void;
    getAllData: <C>() => Promise<C[]>;
    getData: <C>() => C[];
    removeSelectByKey: (key: string) => void;
  }

  export interface Slots {
    domain: () => VNode;
    instanceAddress: () => VNode;
    ip: () => VNode;
    mongodbState: () => VNode;
    operation: () => VNode;
    relatedCluster: () => VNode;
    shard: () => VNode;
  }

  withDefaults(defineProps<Props<T>>(), {
    bkUiSettings: undefined,
    disableSelectMethod: () => false,
    filterValue: undefined,
  });

  const emits = defineEmits<Emits<T>>();

  defineSlots<Slots>();

  const getRowClass = ({ row }: { row: { id: number; isNew: boolean; isOffline: boolean } }) => {
    const classList = [];
    if (row.isNew) {
      classList.push('is-new');
    }
    if (row.isOffline) {
      classList.push('is-offline');
    }
    return classList.join(' ');
  };

  const TABLE_VIEW_MODE_SETTING_KEY = 'INSTANCE_TABLE_VIEW_MODE';

  const { t } = useI18n();
  const userProfileStore = useUserProfile();

  let fetchDataParams: Record<string, any> = {};
  const rootRef = useTemplateRef('root');
  const viewMode = ref<IViewMode>(userProfileStore.profile[TABLE_VIEW_MODE_SETTING_KEY] || 'drawer');
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isFilter = ref(false);
  const isDataRequestSuccess = ref(false);
  const selected = shallowRef<InstanceModel<T>[]>([]);

  const newFeatureGuideList = [
    {
      content: t('注意！实例操作已移到此处，助您更快触达'),
      entry: () => {
        rootRef.value!.querySelectorAll('.t-table__cell--fixed-left').forEach((ele) => {
          (ele as HTMLElement).style.setProperty('z-index', 'unset', 'important');
        });
      },
      leave: () => {
        rootRef.value!.querySelectorAll('.t-table__cell--fixed-left').forEach((ele) => {
          (ele as HTMLElement).style.removeProperty('z-index');
        });
      },
      target: '.instance-list-column-operation-btn',
      title: t('温馨提示'),
    },
  ];

  const fetchData = () => {
    tableRef.value?.fetchData(fetchDataParams);
    isFilter.value = Object.keys(fetchDataParams).length > 0;
  };

  const handleSelection = (keyList: any[], list: InstanceModel<T>[]) => {
    selected.value = list;
    emits('selection', keyList, list);
  };

  const handleTableSettings = (payload: Props<ISupportClusterType>['bkUiSettings']) => {
    userProfileStore.updateProfile({
      label: TABLE_VIEW_MODE_SETTING_KEY,
      values: viewMode.value,
    });
    emits('setting-change', {
      ...payload,
    });
  };
  const handleFilterChange = (filterValue: Record<string, string>) => {
    emits('filter-change', filterValue);
  };

  const handleRequestSuceess = (data: ListBase<InstanceModel<T>[]>) => {
    isDataRequestSuccess.value = true;
    emits('requestSuccess', data);
  };

  defineExpose<Expose>({
    // clearSelected() {
    //   tableRef.value?.clearSelected();
    // },
    fetchData(params: Record<string, any>) {
      fetchDataParams = params;
      fetchData();
    },
    getAllData<T>() {
      return tableRef.value?.fetchAllData<T>() || Promise.resolve([]);
    },
    getData<T>() {
      return tableRef.value?.getData<T>() || [];
    },
    removeSelectByKey(key) {
      tableRef.value?.removeSelectByKey(key);
    },
  });
</script>
<style lang="less">
  .db-instance-table {
    position: relative;

    thead {
      [class*='db-icon'] {
        margin-left: 8px;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    [role='table-cell-operation'] {
      display: none;
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }

    tbody {
      tr {
        &.is-new {
          td {
            background-color: #f3fcf5 !important;
          }
        }

        &.is-offline {
          color: #c4c6cc !important;

          .bk-button.bk-button-primary.is-text {
            color: #c4c6cc !important;
          }
        }

        &.is-selected-row {
          td {
            background: #ebf2ff !important;
          }
        }

        &:hover {
          [role='table-cell-operation'] {
            display: inline-block;
          }
        }
      }
    }

    .is-stand-by {
      color: #531dab !important;
      background: #f9f0ff !important;
    }

    .is-primary {
      color: #531dab !important;
      background: #f9f0ff !important;
    }
  }
</style>
