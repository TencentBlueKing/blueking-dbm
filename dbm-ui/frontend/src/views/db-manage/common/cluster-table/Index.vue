<template>
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
    @selection="handleSelection"
    @setting-change="handleTableSettings">
    <slot name="operation" />
    <slot name="masterDomain" />
    <ClusterAliasColumn
      :cluster-type="clusterType"
      @refresh="handleRefresh" />
    <!-- <slot name="clusterName">
      <ClusterNameColumn
        :cluster-type="clusterType"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :selected-list="selected"
        @refresh="handleRefresh" />
    </slot> -->
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
    getData: <C>() => C[];
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
  const viewMode = ref<IViewMode>(userProfileStore.profile[TABLE_VIEW_MODE_SETTING_KEY] || 'drawer');
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isFilter = ref(false);
  const selected = shallowRef<ClusterModel<T>[]>([]);

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

  defineExpose<Expose>({
    clearSelected() {
      tableRef.value?.clearSelected();
    },
    fetchData(params: Record<string, any>) {
      fetchDataParams = params;
      fetchData();
    },
    getData<T>() {
      return tableRef.value?.getData<T>() || [];
    },
  });
</script>
<style lang="less">
  .db-cluster-table {
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
