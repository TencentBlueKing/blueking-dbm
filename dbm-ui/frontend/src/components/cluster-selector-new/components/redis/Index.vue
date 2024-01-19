<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SerachBar
    v-model="searchSelectValue"
    :cluster-type="activeTab"
    :placeholder="searchPlaceholder"
    :search-select-list="searchSelectList" />
  <BkLoading
    :loading="isLoading"
    :z-index="2">
    <DbOriginalTable
      class="table-box"
      :columns="generatedColumns"
      :data="tableData"
      :is-anomalies="isAnomalies"
      :is-searching="searchSelectValue.length > 0"
      :max-height="528"
      :pagination="pagination.count < 10 ? false : pagination"
      remote-pagination
      row-style="cursor: pointer;"
      @page-limit-change="handleTableLimitChange"
      @page-value-change="handleTablePageChange"
      @refresh="fetchResources"
      @row-click.stop.prevent="handleRowClick" />
  </BkLoading>
</template>
<script setup lang="tsx">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbStatus from '@components/db-status/index.vue';

  import { makeMap } from '@utils';

  import type { TabItem } from '../../Index.vue';
  import SerachBar from '../common/SearchBar.vue';
  import ClusterRelatedTasks from '../common/task-panel/Index.vue';

  import { useClusterData } from './useClusterData';

  interface Props {
    activeTab: string,
    selected: Record<string, any[]>,
    // eslint-disable-next-line vue/no-unused-properties
    getResourceList: TabItem['getResourceList'],
    disabledRowConfig?: TabItem['disabledRowConfig'],
    columnStatusFilter?: TabItem['columnStatusFilter'],
    customColums?: TabItem['customColums'],
    searchSelectList?: TabItem['searchSelectList'],
    searchPlaceholder?: TabItem['searchPlaceholder'],
  }

  type ResourceItem = ValueOf<SelectedMap>[0];

  interface Emits {
    (e: 'change', value: Record<string, Record<string, ResourceItem>>): void,
  }

  type SelectedMap = Props['selected'];

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const columns = [
    {
      width: 60,
      label: () => (
        <bk-checkbox
          key={`${pagination.current}_${activeTab.value}`}
          model-value={isSelectedAll.value}
          indeterminate={isIndeterminate.value}
          disabled={mainSelectDisable.value}
          label={true}
          onChange={handleSelecteAll}
        />
      ),
      render: ({ data }: { data: ResourceItem }) => {
        if (data.phase === 'offline') {
          return (
            <bk-popover
              theme="dark"
              placement="top"
              popoverDelay={0}>
              {{
                default: () => <bk-checkbox style="vertical-align: middle;" disabled />,
                content: () => <span>{t('集群已禁用')}</span>,
              }}
            </bk-popover>
          );
        }
        if (props.disabledRowConfig && props.disabledRowConfig.handler(data)) {
          return (
            <bk-popover
              theme="dark"
              placement="top"
              popoverDelay={0}>
              {{
                default: () => <bk-checkbox style="vertical-align: middle;" disabled />,
                content: () => <span>{props.disabledRowConfig?.tip}</span>,
              }}
            </bk-popover>
          );
        }
        return (
          <bk-checkbox
            style="vertical-align: middle;"
            model-value={Boolean(selectedDomainMap.value[data.id])}
            label={true}
            onChange={(value: boolean) => handleSelecteRow(data, value)}
          />
        );
      },
    },
    {
      label: t('集群'),
      field: 'cluster_name',
      showOverflowTooltip: true,
      render: ({ data }: { data: ResourceItem }) => (
      <div class="cluster-name-box">
          <div class="cluster-name">{data.master_domain}</div>
          {data.phase === 'offline' && (
            <db-icon
              svg
              type="yijinyong"
              class="mr-8"
              style="width: 38px; height: 16px;" />
          )}
          {data.operations && data.operations.length > 0 && (
            <bk-popover
              theme="light"
              width="360">
              {{
                default: () => <bk-tag theme="info" class="tag-box">{data.operations.length}</bk-tag>,
                content: () => <ClusterRelatedTasks data={data.operations} />,
              }}
            </bk-popover>
          )}
      </div>),
    },
    {
      label: t('状态'),
      field: 'status',
      width: 100,
      render: ({ data }: { data: ResourceItem }) => {
        const isNormal = props.columnStatusFilter ? props.columnStatusFilter(data) : data.status === 'normal';
        const info = isNormal ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('集群别名'),
      field: 'cluster_name',
      showOverflowTooltip: true,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      showOverflowTooltip: true,
    },
  ];

  let isSelectedAllReal = false;

  const activeTab = ref(props.activeTab);
  const selectedMap = shallowRef<Record<string, Record<string, ResourceItem>>>({});
  const isSelectedAll = ref(false);

  const {
    isLoading,
    pagination,
    isAnomalies,
    data: tableData,
    searchSelectValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useClusterData<ResourceItem>();

  // 选中域名列表
  const selectedDomainMap = computed(() => Object.values(selectedMap.value)
    .reduce((result, selectItem) => {
      const masterDomainMap  = makeMap(Object.keys(selectItem));
      return Object.assign({}, result, masterDomainMap);
    }, {} as Record<string, boolean>));

  const isIndeterminate = computed(() => !isSelectedAll.value
    && selectedMap.value[activeTab.value] && Object.keys(selectedMap.value[activeTab.value]).length > 0);

  const mainSelectDisable = computed(() => (props.disabledRowConfig
    // eslint-disable-next-line max-len
    ? tableData.value.filter(data => props.disabledRowConfig?.handler(data)).length === tableData.value.length : false));

  const generatedColumns = computed(() => {
    if (props.customColums) {
      return [columns[0], ...props.customColums];
    }
    return columns;
  });

  watch(() => [props.activeTab, props.selected] as [string, Record<string, any[]>], ([tabKey, selected]) => {
    if (tabKey) {
      activeTab.value = tabKey;
      if (!selected[tabKey] || !props.selected) {
        return;
      }
      const tabSelectMap = selected[tabKey].reduce((selectResult, selectItem) => ({
        ...selectResult,
        [selectItem.id]: selectItem,
      }), {} as Record<string, ResourceItem>);
      selectedMap.value = {
        [tabKey]: tabSelectMap,
      };
    }
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => activeTab.value, (tab) => {
    if (tab) {
      searchSelectValue.value = [];
    }
  });

  watch(isLoading, (status) => {
    if (!status) {
      checkSelectedAll();
    }
  });

  /**
   * 全选当页数据
   */
  const handleSelecteAll = (value: boolean) => {
    if (props.disabledRowConfig) {
      isSelectedAllReal = !isSelectedAllReal;
      for (const data of tableData.value) {
        if (!props.disabledRowConfig.handler(data)) {
          handleSelecteRow(data, isSelectedAllReal);
        }
      }
      return;
    }
    for (const data of tableData.value) {
      if (data.phase !== 'offline') {
        handleSelecteRow(data, value);
      }
    }
  };

  const checkSelectedAll = () => {
    if (props.disabledRowConfig && tableData.value.filter(data => props.disabledRowConfig?.handler(data)).length > 0) {
      nextTick(() => {
        isSelectedAll.value = false;
      });
      return;
    }
    const currentSelected = selectedMap.value[activeTab.value];
    if (!currentSelected || Object.keys(currentSelected).length < 1) {
      isSelectedAll.value = false;
      return;
    }
    for (let i = 0; i < tableData.value.length; i++) {
      if (!currentSelected[tableData.value[i].id]) {
        isSelectedAll.value = false;
        return;
      }
    }
    isSelectedAll.value = true;
  };

  /**
   * 选择当行数据
   */
  const handleSelecteRow = (data: ResourceItem, value: boolean) => {
    const selectedMapMemo = { ...selectedMap.value };
    if (!selectedMapMemo[activeTab.value]) {
      selectedMapMemo[activeTab.value] = {};
    }
    if (value) {
      selectedMapMemo[activeTab.value][data.id] = data;
    } else {
      delete selectedMapMemo[activeTab.value][data.id];
    }
    selectedMap.value = selectedMapMemo;
    emits('change', selectedMap.value);
    checkSelectedAll();
  };

  const handleRowClick = (row:any, data: ResourceItem) => {
    if ((props.disabledRowConfig && props.disabledRowConfig.handler(data)) || data.phase === 'offline') {
      return;
    }
    const currentSelected = selectedMap.value[activeTab.value];
    const isChecked = !!(currentSelected && currentSelected[data.id]);
    handleSelecteRow(data, !isChecked);
  };


  const handleTablePageChange = (value: number) => {
    handleChangePage(value)
      .then(() => {
        checkSelectedAll();
      });
  };

  const handleTableLimitChange = (value: number) => {
    handeChangeLimit(value)
      .then(() => {
        checkSelectedAll();
      });
  };
</script>

<style lang="less" scoped>
.table-box {
  :deep(.cluster-name-box) {
    display: flex;
    width: 100%;
    align-items: center;
    overflow: hidden;

    .cluster-name {
      width: auto;
      margin-right: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .tag-box {
      height: 16px;
      color: #3A84FF;
      border-radius: 8px !important;
    }
  }
}
</style>

