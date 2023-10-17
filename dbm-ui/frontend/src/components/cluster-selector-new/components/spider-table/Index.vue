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
    @search="handleSearch" />
  <BkLoading
    :loading="isLoading"
    :z-index="2">
    <DbOriginalTable
      class="table-box"
      :columns="columns"
      :data="tableData"
      :height="528"
      :is-anomalies="isAnomalies"
      :is-searching="searchSelectValue.length > 0"
      :pagination="pagination.count < 10 ? false: pagination"
      remote-pagination
      row-style="cursor: pointer;"
      @page-limit-change="handleTableLimitChange"
      @page-value-change="handleTablePageChange"
      @refresh="fetchResources"
      @row-click.stop="handleRowClick" />
  </BkLoading>
</template>
<script setup lang="tsx" generic="T extends SpiderModel">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SpiderModel from '@services/model/spider/spider';
  import type { ResourceItem } from '@services/types/clusters';
  import type { ListBase } from '@services/types/common';

  import DbStatus from '@components/db-status/index.vue';

  import {
    makeMap,
  } from '@utils';

  import ClusterRelatedTasks from '../task-panel/Index.vue';

  import SerachBar from './SearchBar.vue';
  import { useClusterData } from './useSpiderClusterData';

  interface Props {
    activeTab: string,
    selected: Record<string, T[]>,
    // eslint-disable-next-line vue/no-unused-properties
    getResourceList: (params: Record<string, any>) => Promise<ListBase<T[]>>
  }

  interface Emits {
    (e: 'change', value: Record<string, Record<string, ValueOf<SelectedMap>[0]>>): void,
  }

  type SelectedMap = Props['selected'];

  type ValueOf<T> = T[keyof T]

  const props = withDefaults(defineProps<Props>(), {
    selected: () =>  ({}),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const activeTab = ref(props.activeTab);
  const searchSelectValue = ref<ISearchValue[]>([]);
  const selectedMap = shallowRef<Record<string, Record<string, ValueOf<SelectedMap>[0]>>>({});
  const isSelectedAll = ref(false);

  const {
    isLoading,
    pagination,
    isAnomalies,
    data: tableData,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useClusterData<ValueOf<SelectedMap>[0]>(activeTab, searchSelectValue);

  // 选中域名列表
  const selectedDomainMap = computed(() => Object.values(selectedMap.value)
    .reduce((result, selectItem) => {
      const masterDomainMap  = makeMap(Object.keys(selectItem));
      return Object.assign({}, result, masterDomainMap);
    }, {} as Record<string, boolean>));

  const isIndeterminate = computed(() => !isSelectedAll.value
    && selectedMap.value[activeTab.value] && Object.keys(selectedMap.value[activeTab.value]).length > 0);

  const columns = [
    {
      width: 60,
      label: () => (
        <bk-checkbox
          key={`${pagination.current}_${activeTab.value}`}
          model-value={isSelectedAll.value}
          indeterminate={isIndeterminate.value}
          label={true}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={handleSelecteAll}
        />
      ),
      render: ({ data }: { data: ValueOf<SelectedMap>[0] }) => (
        <bk-checkbox
          style="vertical-align: middle;"
          model-value={Boolean(selectedDomainMap.value[data.id])}
          label={true}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={(value: boolean) => handleSelecteRow(data, value)}
        />
      ),
    },
    {
      label: t('集群'),
      field: 'cluster_name',
      showOverflowTooltip: true,
      render: ({ data }: { data: ResourceItem }) => (
      <div class="cluster-name-box">
          <div class="cluster-name">{data.master_domain}</div>
          {data.operations && data.operations.length > 0 && <bk-popover
            theme="light"
            width="360">
            {{
              default: () => <bk-tag theme="info" class="tag-box">{data.operations.length}</bk-tag>,
              content: () => <ClusterRelatedTasks data={data.operations} />,
            }}
          </bk-popover>}
      </div>),
    },
    {
      label: t('域名'),
      field: 'master_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      showOverflowTooltip: true,
    },
    {
      label: t('所属模块'),
      field: 'db_module_name',
      showOverflowTooltip: true,
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 100,
      render: ({ data }: { data: ResourceItem }) => {
        const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
  ];

  watch(() => [props.activeTab, props.selected] as [string, Record<string, T[]>], ([tabKey, selected]) => {
    if (tabKey) {
      activeTab.value = tabKey;
      if (!selected[tabKey] || !props.selected) {
        return;
      }
      const tabSelectMap = selected[tabKey].reduce((selectResult, selectItem) => ({
        ...selectResult,
        [selectItem.id]: selectItem,
      }), {} as Record<string, ValueOf<SelectedMap>[0]>);
      selectedMap.value = {
        [tabKey]: tabSelectMap,
      };
    }
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => activeTab.value, () => {
    searchSelectValue.value = [];
    handleTablePageChange(1);
  });


  /**
   * 过滤列表
   */
  const handleSearch = () => {
    nextTick(() => {
      handleTablePageChange(1);
    });
  };

  /**
   * 全选当页数据
   */
  const handleSelecteAll = (value: boolean) => {
    for (const data of tableData.value) {
      handleSelecteRow(data, value);
    }
  };

  const checkSelectedAll = () => {
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
  const handleSelecteRow = (data: ValueOf<SelectedMap>[0], value: boolean) => {
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

  const handleRowClick = (row:any, data: ValueOf<SelectedMap>[0]) => {
    const currentSelected = selectedMap.value[activeTab.value];
    const isChecked = !!(currentSelected && currentSelected[data.id]);
    handleSelecteRow(data, !isChecked);
  };


  function handleTablePageChange(value: number) {
    handleChangePage(value)
      .then(() => {
        checkSelectedAll();
      });
  }

  function handleTableLimitChange(value: number) {
    handeChangeLimit(value)
      .then(() => {
        checkSelectedAll();
      });
  }
</script>

<style lang="less" scoped>
.table-box {
  :deep(.cluster-name-box) {
    display: flex;
    width: 100%;
    align-items: center;
    overflow: hidden;

    .cluster-name {
      margin-right: 8px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      flex:1;
    }

    .tag-box {
      height: 16px;
      color: #3A84FF;
      border-radius: 8px !important;
    }
  }
}
</style>

