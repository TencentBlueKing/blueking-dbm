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
    v-model="searchValue"
    :cluster-type="activeTab"
    :search-attrs="searchAttrs"
    :search-select-list="searchSelectList"
    @search-value-change="handleSearchValueChange"
    @tag-value-change="fetchResources" />
  <BkLoading
    :loading="isLoading"
    :z-index="2">
    <PrimaryTable
      class="table-box"
      :columns="generatedColumns"
      :data="tableData"
      :filter-value="columnCheckedMap"
      :max-height="528"
      :row-class-name="getRowClass"
      row-key="id"
      @filter-change="handleFilterChange"
      @row-click="handleRowClick">
      <template #empty>
        <EmptyStatus
          :is-anomalies="isAnomalies"
          :is-searching="searchValue.length > 0"
          @clear-search="clearSearchValue"
          @refresh="fetchResources" />
      </template>
    </PrimaryTable>
    <div class="table-footer">
      <BkPagination
        v-bind="pagination"
        :model-value="pagination.current"
        @change="handleTablePageChange"
        @limit-change="handleTableLimitChange" />
    </div>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { Checkbox, type PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  import type { TabItem } from '../../Index.vue';
  import { tagsColumn, transBkuiColumns } from '../common/columns';
  import SerachBar from '../common/SearchBar.vue';
  import ClusterRelatedTasks from '../common/task-panel/Index.vue';

  import { useClusterData } from './useClusterData';

  interface Props {
    activeTab: ClusterTypes;
    columnStatusFilter?: TabItem['columnStatusFilter'];
    customColums?: TabItem['customColums'];
    disabledRowConfig: NonNullable<TabItem['disabledRowConfig']>;
    getResourceList: NonNullable<TabItem['getResourceList']>;
    // 多选模式
    multiple: TabItem['multiple'];
    searchSelectList?: TabItem['searchSelectList'];
    selected: any[];
  }

  type Emits = (e: 'change', value: ResourceItem[]) => void;

  type SelectedMap = Props['selected'];

  type ResourceItem = ValueOf<SelectedMap>[0];

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const checkSelectedAll = () => {
    if (tableData.value.filter((data) => props.disabledRowConfig.find((item) => item.handler(data))).length > 0) {
      isSelectedAll.value = false;
      return;
    }

    if (!selectedList.value.length) {
      isSelectedAll.value = false;
      return;
    }

    // eslint-disable-next-line @typescript-eslint/prefer-for-of
    for (let i = 0; i < tableData.value.length; i++) {
      const data = tableData.value[i];
      if (!selectedMap.value[`${data.id}:${data.master_domain}`]) {
        isSelectedAll.value = false;
        return;
      }
    }
    isSelectedAll.value = true;
  };

  const { t } = useI18n();

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    tableColumnFilterChange,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    searchType: ClusterTypes.TENDBHA,
  });

  const {
    data: tableData,
    fetchResources,
    handeChangeLimit,
    handleChangePage,
    isAnomalies,
    isLoading,
    pagination,
  } = useClusterData<ResourceItem>(searchValue);

  const activeTab = ref(props.activeTab);
  const selectedList = ref<ResourceItem[]>([]);
  const isSelectedAll = ref(false);

  const selectedMap = computed(() =>
    selectedList.value.reduce<Record<string, ResourceItem>>((results, item) => {
      Object.assign(results, {
        [`${item.id}:${item.master_domain}`]: item,
      });
      return results;
    }, {}),
  );

  const statusFilterList = computed(() => [
    {
      label: t('正常'),
      value: 'normal',
    },
    {
      label: t('异常'),
      value: 'abnormal',
    },
  ]);

  const columns = computed<PrimaryTableCol[]>(() => [
    {
      cell: (_, { row }) => {
        const disabledRowConfig = props.disabledRowConfig.find((item) => item.handler(row));
        if (disabledRowConfig) {
          return (
            <bk-popover
              placement='top'
              popoverDelay={0}
              theme='dark'>
              {{
                content: () => <span>{disabledRowConfig.tip}</span>,
                default: () =>
                  props.multiple ? (
                    <Checkbox
                      disabled
                      style='vertical-align: middle;'
                    />
                  ) : (
                    <bk-radio
                      disabled
                      label={false}
                    />
                  ),
              }}
            </bk-popover>
          );
        }
        return props.multiple ? (
          <span onClick={(e: Event) => e.stopPropagation()}>
            <Checkbox
              checked={Boolean(selectedMap.value[`${row.id}:${row.master_domain}`])}
              style='vertical-align: middle;'
              onChange={(value: boolean) => handleSelecteRow(row, value)}
            />
          </span>
        ) : (
          <bk-radio-group
            model-value={Boolean(selectedMap.value[`${row.id}:${row.master_domain}`])}
            onChange={(value: boolean) => handleSelecteRow(row, value)}>
            <bk-radio label={true} />
          </bk-radio-group>
        );
      },
      colKey: 'row-select',
      minWidth: 70,
      title: () =>
        props.multiple && (
          <div style='display:flex;align-items:center'>
            <Checkbox
              key={`${pagination.current}_${activeTab.value}`}
              checked={isSelectedAll.value}
              disabled={mainSelectDisable.value}
              indeterminate={isIndeterminate.value}
              onChange={handleWholeSelect}
            />
            {/* <bk-popover
            placement="bottom-start"
            theme="light db-table-select-menu"
            arrow={ false }
            trigger='hover'
            v-slots={{
              default: () => <db-icon class="select-menu-flag" type="down-big" />,
              content: () => (
                <div class="db-table-select-plan">
                  <div
                    class="item"
                    onClick={handleWholeSelect}>{t('跨页全选')}</div>
                </div>
              ),
            }}>
          </bk-popover> */}
          </div>
        ),
    },
    {
      cell: (_, { row }) => (
        <TextOverflowLayout class='cluster-name-box'>
          {{
            append: () => (
              <>
                {row.operations && row.operations.length > 0 && (
                  <bk-popover
                    theme='light'
                    width='360'>
                    {{
                      content: () => <ClusterRelatedTasks data={row.operations} />,
                      default: () => (
                        <bk-tag
                          class='tag-box'
                          theme='info'>
                          {row.operations.length}
                        </bk-tag>
                      ),
                    }}
                  </bk-popover>
                )}
                {row.isOffline && (
                  <bk-tag
                    class='ml-4'
                    size='small'>
                    {t('已禁用')}
                  </bk-tag>
                )}
              </>
            ),
            default: () => <span class='cluster-name'>{row.master_domain}</span>,
          }}
        </TextOverflowLayout>
      ),
      colKey: 'master_domain',
      ellipsis: true,
      minWidth: 280,
      title: t('访问入口'),
    },
    tagsColumn,
    {
      cell: (_, { row }) => {
        const isNormal = props.columnStatusFilter ? props.columnStatusFilter(row) : row.status === 'normal';
        const info = isNormal ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      colKey: 'status',
      filter: {
        list: statusFilterList.value,
        showConfirmAndReset: true,
        type: 'multiple',
      },
      minWidth: 80,
      title: t('状态'),
    },
    {
      colKey: 'cluster_name',
      ellipsis: true,
      minWidth: 120,
      title: t('集群名称'),
    },
    {
      cell: (_, { row }) => <span>{row.db_module_name || '--'}</span>,
      colKey: 'db_module_id',
      ellipsis: true,
      filter: {
        list: (columnAttrs.value.db_module_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        showConfirmAndReset: true,
        type: 'multiple',
      },
      minWidth: 100,
      title: t('所属模块'),
    },
    {
      cell: (_, { row }) => <span>{row.bk_cloud_name}</span>,
      colKey: 'bk_cloud_id',
      ellipsis: true,
      filter: {
        list: (columnAttrs.value.bk_cloud_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        showConfirmAndReset: true,
        type: 'multiple',
      },
      minWidth: 100,
      title: t('管控区域'),
    },
  ]);

  const isIndeterminate = computed(() => !isSelectedAll.value && selectedList.value.length > 0);

  const mainSelectDisable = computed(
    () =>
      tableData.value.filter((data) => props.disabledRowConfig.find((item) => item.handler(data))).length ===
      tableData.value.length,
  );

  const generatedColumns = computed<PrimaryTableCol[]>(() => {
    if (props.customColums) {
      return [columns.value[0], ...transBkuiColumns(props.customColums)];
    }
    return columns.value;
  });

  const handleFilterChange = (filterValue: Record<string, string[]>) => {
    tableColumnFilterChange(filterValue, {
      bk_cloud_id: {
        list: (columnAttrs.value.bk_cloud_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        name: t('管控区域'),
      },
      db_module_id: {
        list: (columnAttrs.value.db_module_id || []).map((item) => ({
          label: item.text,
          value: item.value,
        })),
        name: t('所属模块'),
      },
      status: {
        list: statusFilterList.value,
        name: t('状态'),
      },
    });
  };

  watch(
    () => [props.activeTab, props.selected],
    () => {
      if (props.activeTab) {
        activeTab.value = props.activeTab;
        selectedList.value = props.selected;
        checkSelectedAll();
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  watch(
    () => activeTab.value,
    () => {
      if (activeTab.value) {
        searchValue.value = [];
        handleTablePageChange(1);
      }
    },
  );

  watch(searchValue, () => {
    selectedList.value = [];
    emits('change', []);
  });

  const getRowClass = ({ row }: { row: ResourceItem }) => row.isOffline && 'is-offline';

  // 跨页全选
  const handleWholeSelect = (value: boolean) => {
    if (value) {
      isLoading.value = true;
      props
        .getResourceList({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          limit: -1,
          offset: 0,
          ...getSearchSelectorParams(searchValue.value),
        })
        .then((data) => {
          data.results.forEach((dataItem) => {
            if (!props.disabledRowConfig.find((item) => item.handler(dataItem))) {
              handleSelecteRow(dataItem, true);
            }
          });
        })
        .finally(() => (isLoading.value = false));
    } else {
      selectedList.value = [];
      emits('change', []);
    }
  };

  /**
   * 全选当页数据
   */
  // const handleSelecteAll = (value: boolean) => {
  //   for (const data of tableData.value) {
  //     if (!props.disabledRowConfig.find(item => item.handler(data))) {
  //       handleSelecteRow(data, value);
  //     }
  //   }
  // };

  /**
   * 选择当行数据
   */
  const handleSelecteRow = (data: ResourceItem, value: boolean) => {
    if (!props.multiple) {
      selectedList.value = [];
    }
    if (value && !selectedMap.value[`${data.id}:${data.master_domain}`]) {
      selectedList.value.push(data);
    } else {
      selectedList.value = selectedList.value.filter((item) => item.id !== data.id);
    }
    emits('change', selectedList.value);
    checkSelectedAll();
  };

  const handleRowClick = ({ row }: { row: ResourceItem }) => {
    if (props.disabledRowConfig.find((item) => item.handler(row))) {
      return;
    }

    const isChecked = !!selectedMap.value[`${row.id}:${row.master_domain}`];
    handleSelecteRow(row, !isChecked);
  };

  const handleTablePageChange = (value: number) => {
    pagination.current = value;
    handleChangePage(value).then(() => {
      checkSelectedAll();
    });
  };

  const handleTableLimitChange = (value: number) => {
    handeChangeLimit(value).then(() => {
      checkSelectedAll();
    });
  };
</script>

<style lang="less" scoped>
  .table-box {
    :deep(.t-table__body) {
      tr {
        cursor: pointer;
      }
    }

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
        color: #3a84ff;
        border-radius: 8px !important;
      }
    }
  }

  .table-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }
</style>
