<template>
  <div ref="root">
    <DbTable
      ref="tableRef"
      class="db-cluster-table"
      :data-source="dataSource"
      :disable-select-method="disableSelectMethod"
      releate-url-query
      :row-class="getRowClass"
      :row-config="{
        useKey: true,
        keyField: 'id',
      }"
      v-bind="$attrs"
      :scroll-y="{ enabled: true, gt: 0 }"
      selectable
      :settings="settings"
      :show-overflow="false"
      show-settings
      @request-success="handleRequestSuceess"
      @selection="handleSelection"
      @setting-change="handleTableSettings">
      <slot
        :key="tableRef?.loading"
        name="operation" />
      <slot name="masterDomain" />
      <ClusterAliasColumn
        :cluster-type="clusterType"
        @refresh="handleRefresh" />
      <slot name="slaveDomain" />
      <slot name="clusterTag">
        <ClusterTagColumn
          :cluster-type="clusterType"
          @refresh="handleRefresh" />
      </slot>
      <slot name="status">
        <StatusColumn :cluster-type="clusterType" />
      </slot>
      <slot name="clusterState">
        <ClusterStatsColumn :cluster-type="clusterType" />
      </slot>
      <slot name="role" />
      <slot name="clusterTypeName" />
      <slot name="syncMode" />
      <slot name="moduleNames" />
      <CommonColumn :cluster-type="clusterType" />
      <template #setting>
        <div>
          <div class="mb-8">{{ t('详情打开方式') }}</div>
          <BkRadioGroup
            v-model="viewMode"
            style="display: flex">
            <BkRadioButton
              label="drawer"
              style="flex: 1">
              {{ t('抽屉侧滑') }}
            </BkRadioButton>
            <BkRadioButton
              label="jump"
              style="flex: 1">
              {{ t('新窗口') }}
            </BkRadioButton>
          </BkRadioGroup>
        </div>
      </template>
    </DbTable>
    <NewFeatureGuide
      v-if="isDataRequestSuccess"
      :list="newFeatureGuideList"
      name="cluster_list" />
  </div>
</template>
<script lang="ts">
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ClusterAliasColumn from './ClusterAliasColumn.vue';
  import ClusterNameColumn from './ClusterNameColumn.vue';
  import ClusterStatsColumn from './ClusterStatsColumn.vue';
  import ClusterTagColumn from './ClusterTagColumn.vue';
  import CommonColumn from './CommonColumn.vue';
  import IdColumn from './IdColumn.vue';
  import MasterDomainColumn from './MasterDomainColumn.vue';
  import ModuleNameColumn from './ModuleNameColumn.vue';
  import OperationColumn from './OperationColumn.vue';
  import RoleColumn from './RoleColumn.vue';
  import SlaveDomainColumn from './SlaveDomainColumn.vue';
  import StatusColumn from './StatusColumn.vue';

  export {
    ClusterNameColumn,
    ClusterStatsColumn,
    ClusterTagColumn,
    CommonColumn,
    IdColumn,
    MasterDomainColumn,
    ModuleNameColumn,
    OperationColumn,
    RoleColumn,
    SlaveDomainColumn,
    StatusColumn,
  };

  type IViewMode = 'drawer' | 'jump';
</script>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useUserProfile } from '@stores';

  import DbTable, { type Props as DbTableProps } from '@components/db-table/index.vue';

  import type { ClusterModel, ISupportClusterType } from './types.ts';

  export interface Props<C extends ISupportClusterType> {
    clusterId: number;
    clusterType: C;
    disableSelectMethod?: (data: any) => boolean;
    settings?: {
      checked?: string[];
      disabled?: string[];
      size?: 'medium' | 'mini' | 'small';
    };
  }

  export interface Emits<C extends ISupportClusterType> {
    (e: 'selection', key: number[], list: ClusterModel<C>[]): void;
    (e: 'setting-change', params: NonNullable<Props<C>['settings']>): void;
  }

  export interface Expose {
    clearSelected: () => void;
    fetchData: (params: Record<string, any>) => void;
    getAllData: <C>() => Promise<C[]>;
    getData: <C>() => C[];
    removeSelectByKey: (key: string) => void;
  }

  export interface Slots {
    clusterName: () => VNode;
    clusterState: () => VNode;
    clusterTag: () => VNode;
    clusterTypeName: () => VNode;
    masterDomain: () => VNode;
    moduleNames: () => VNode;
    operation: () => VNode;
    role: () => VNode;
    slaveDomain: () => VNode;
    status: () => VNode;
    syncMode: () => VNode;
  }

  const props = withDefaults(defineProps<DbTableProps & Props<T>>(), {
    disableSelectMethod: () => false,
    settings: undefined,
  });

  const emits = defineEmits<Emits<T>>();

  defineSlots<Slots>();

  const getRowClass = (data: { id: number; isNew: boolean; isOnline: boolean }) => {
    const classList = [];
    if (data.isNew) {
      classList.push('is-new');
    }
    if (!data.isOnline) {
      classList.push('is-offline');
    }
    if (data.id === props.clusterId) {
      classList.push('is-selected-row');
    }
    return classList.join(' ');
  };

  const TABLE_VIEW_MODE_SETTING_KEY = 'CLUSTER_TABLE_VIEW_MODE';

  const { t } = useI18n();
  const userProfileStore = useUserProfile();

  let fetchDataParams: Record<string, any> = {};
  const rootRef = useTemplateRef('root');
  const viewMode = ref<IViewMode>(userProfileStore.profile[TABLE_VIEW_MODE_SETTING_KEY] || 'drawer');
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isFilter = ref(false);
  const isDataRequestSuccess = ref(false);
  const selected = shallowRef<ClusterModel<T>[]>([]);

  const newFeatureGuideList = [
    {
      content: t('注意！集群操作已移到此处，助您更快触达'),
      entry: () => {
        const fixZIndexEle = rootRef.value!.querySelector('.vxe-table--fixed-left-wrapper');
        if (fixZIndexEle) {
          (fixZIndexEle as HTMLElement).style.zIndex = 'unset !important';
        }
      },
      leave: () => {
        const fixZIndexEle = rootRef.value!.querySelector('.vxe-table--fixed-left-wrapper');
        if (fixZIndexEle) {
          (fixZIndexEle as HTMLElement).style.zIndex = '';
        }
      },
      target: '.cluster-list-column-operation-btn',
      title: t('温馨提示'),
    },
  ];

  const fetchData = () => {
    tableRef.value?.fetchData(fetchDataParams);
    isFilter.value = Object.keys(fetchDataParams).length > 0;
  };

  const handleRefresh = () => {
    fetchData();
  };

  const handleSelection = (keyList: any[], list: ClusterModel<T>[]) => {
    selected.value = list;
    emits('selection', keyList, list);
  };

  const handleTableSettings = (payload: Props<ISupportClusterType>['settings']) => {
    userProfileStore.updateProfile({
      label: TABLE_VIEW_MODE_SETTING_KEY,
      values: viewMode.value,
    });
    emits('setting-change', {
      ...payload,
    });
  };

  const handleRequestSuceess = () => {
    isDataRequestSuccess.value = true;
  };

  defineExpose<Expose>({
    clearSelected() {
      tableRef.value?.clearSelected();
    },
    fetchData(params: Record<string, any>) {
      fetchDataParams = params;
      fetchData();
    },
    getAllData<T>() {
      return tableRef.value?.getAllData<T>() || Promise.resolve([]);
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
  .db-cluster-table {
    position: relative;

    tr {
      &.is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }

      &.is-offline {
        .vxe-cell,
        .bk-button.bk-button-primary.is-text {
          color: #c4c6cc !important;
        }
      }

      &.is-selected-row {
        td {
          background: #ebf2ff !important;
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
