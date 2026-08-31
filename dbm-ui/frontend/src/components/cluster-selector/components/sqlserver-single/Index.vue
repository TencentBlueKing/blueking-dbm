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
    :search-select-list="searchSelectList" />
  <BkLoading
    :loading="isLoading"
    :z-index="2">
    <PrimaryTable
      class="table-box"
      :columns="generatedColumns"
      :data="tableData"
      :filter-value="searchValue"
      :max-height="472"
      row-key="id"
      @filter-change="handleFilterChange"
      @row-click="handleRowClick">
      <template #empty>
        <EmptyStatus
          :is-anomalies="isAnomalies"
          :is-searching="Object.keys(searchValue).length > 0"
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

  import { useSelectorSearch } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterDetailRelatedTicket from '@views/db-manage/common/ClusterDetailRelatedTicket.vue';

  import { transfromDataToQuery } from '@utils';

  import type { TabItem } from '../../Index.vue';
  import { tagsColumn, transBkuiColumns } from '../common/columns';
  import SerachBar from '../common/SearchBar.vue';

  import { useClusterData } from './useClusterData';

  interface Props {
    activeTab: ClusterTypes;
    columnStatusFilter?: TabItem['columnStatusFilter'];
    customColums?: TabItem['customColums'];
    disabledRowConfig: NonNullable<TabItem['disabledRowConfig']>;
    getResourceList: NonNullable<TabItem['getResourceList']>;
    multiple: boolean;
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
      if (!selectedMap.value[tableData.value[i].id]) {
        isSelectedAll.value = false;
        return;
      }
    }
    isSelectedAll.value = true;
  };

  const { t } = useI18n();

  const { clearSearchValue, columnAttrs, handleFilterChange, searchAttrs, searchValue } = useSelectorSearch(
    ClusterTypes.SQLSERVER_SINGLE,
    ['bk_cloud_id', 'db_module_id', 'major_version'],
  );

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
        [item.id]: item,
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
              checked={Boolean(selectedMap.value[row.id])}
              style='vertical-align: middle;'
              onChange={(value: boolean) => handleSelecteRow(row, value)}
            />
          </span>
        ) : (
          <bk-radio
            label={true}
            model-value={Boolean(selectedMap.value[row.id])}
            onChange={(value: boolean) => handleSelecteRow(row, value)}
          />
        );
      },
      colKey: 'row-select',
      fixed: 'left',
      title: () =>
        props.multiple ? (
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
        ) : (
          ''
        ),
      width: 36,
    },
    {
      cell: (_, { row }) => (
        <TextOverflowLayout class='cluster-name-box'>
          {{
            append: () => (
              <>
                {!row.isOnline && (
                  <bk-tag
                    class='ml-8'
                    size='small'>
                    {t('已禁用')}
                  </bk-tag>
                )}
                {row.operations && row.operations.length > 0 && <ClusterDetailRelatedTicket data={row.operations} />}
              </>
            ),
            default: () => <span class='cluster-name'>{row.master_domain}</span>,
          }}
        </TextOverflowLayout>
      ),
      colKey: 'master_domain',
      ellipsis: true,
      fixed: 'left',
      title: t('访问入口'),
      width: 280,
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
      title: t('状态'),
      width: 90,
    },
    {
      colKey: 'cluster_name',
      ellipsis: true,
      title: t('集群名称'),
      width: 200,
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
      title: t('所属模块'),
      width: 150,
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
      title: t('管控区域'),
      width: 120,
    },
    {
      cell: (_, { row }) => row.major_version || '--',
      colKey: 'major_version',
      ellipsis: true,
      title: t('版本'),
      width: 200,
    },
    {
      cell: (_, { row }) => <span>{row.sync_mode || '--'}</span>,
      colKey: 'sync_mode',
      minWidth: 120,
      title: t('同步模式'),
      width: 120,
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
        searchValue.value = {};
      }
    },
  );

  watch(isLoading, (status) => {
    if (!status) {
      checkSelectedAll();
    }
  });

  watch(searchValue, () => {
    selectedList.value = [];
    emits('change', []);
  });

  // 跨页全选
  const handleWholeSelect = (value: boolean) => {
    if (value) {
      isLoading.value = true;
      props
        .getResourceList({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          limit: -1,
          offset: 0,
          ...transfromDataToQuery(searchValue.value),
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
    if (value && !selectedMap.value[data.id]) {
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

    const isChecked = !!selectedMap.value[row.id];
    handleSelecteRow(row, !isChecked);
  };

  const handleTablePageChange = (value: number) => {
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
    }
  }

  .table-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
  }
</style>
