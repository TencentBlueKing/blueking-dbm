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
    @search-value-change="handleSearchValueChange" />
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
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @page-limit-change="handleTableLimitChange"
      @page-value-change="handleTablePageChange"
      @refresh="fetchResources"
      @row-click.stop.prevent="handleRowClick" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { getSearchSelectorParams } from '@utils';

  import type { TabItem } from '../../Index.vue';
  import SerachBar from '../common/SearchBar.vue';
  import ClusterRelatedTasks from '../common/task-panel/Index.vue';

  import { useClusterData } from './useClusterData';

  interface Props {
    activeTab: ClusterTypes,
    selected: any[],
    getResourceList: NonNullable<TabItem['getResourceList']>,
    disabledRowConfig: NonNullable<TabItem['disabledRowConfig']>,
    columnStatusFilter?: TabItem['columnStatusFilter'],
    customColums?: TabItem['customColums'],
    searchSelectList?: TabItem['searchSelectList'],
    multiple: boolean,
  }

  interface Emits {
    (e: 'change', value: ResourceItem[]): void,
  }

  type SelectedMap = Props['selected'];

  type ResourceItem = ValueOf<SelectedMap>[0];

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const checkSelectedAll = () => {
    if (tableData.value.filter(data => props.disabledRowConfig.find(item => item.handler(data))).length > 0) {
      isSelectedAll.value = false;
      return;
    }

    if (!selectedList.value.length) {
      isSelectedAll.value = false;
      return;
    }

    for (let i = 0; i < tableData.value.length; i++) {
      if (!selectedMap.value[tableData.value[i].id]) {
        isSelectedAll.value = false;
        return;
      }
    }
    isSelectedAll.value = true;
  };

  const { t } = useI18n();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    columnCheckedMap,
    clearSearchValue,
    columnFilterChange,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.SQLSERVER_SINGLE,
    attrs: [
      'bk_cloud_id',
      'db_module_id',
      'major_version',
    ],
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });


  const {
    isLoading,
    pagination,
    isAnomalies,
    data: tableData,
    searchSelectValue,
    fetchResources,
    handleChangePage,
    handeChangeLimit,
  } = useClusterData<ResourceItem>(searchValue);

  const activeTab = ref(props.activeTab);
  const selectedList = ref<ResourceItem[]>([]);
  const isSelectedAll = ref(false);

  const selectedMap = computed(() => selectedList.value.reduce<Record<string, ResourceItem>>((results, item) => {
    Object.assign(results, {
      [item.id]: item,
    })
    return results;
  }, {}))

  const columns = computed(() => [
    {
      width: 80,
      minWidth: 80,
      fixed: 'left',
      label: () => props.multiple ? (
        <div style="display:flex;align-items:center">
          <bk-checkbox
            key={`${pagination.current}_${activeTab.value}`}
            model-value={isSelectedAll.value}
            indeterminate={isIndeterminate.value}
            disabled={mainSelectDisable.value}
            label={true}
            onClick={(e: Event) => e.stopPropagation()}
            onChange={handleSelecteAll}
          />
          <bk-popover
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
          </bk-popover>
        </div>
      ) : '',
      render: ({ data }: { data: ResourceItem }) => {
        const disabledRowConfig = props.disabledRowConfig.find(item => item.handler(data));
        if (disabledRowConfig) {
          return (
            <bk-popover
              theme="dark"
              placement="top"
              popoverDelay={0}>
              {{
                default: () => props.multiple ? <bk-checkbox style="vertical-align: middle;" disabled /> : <bk-radio disabled label={false}/>,
                content: () => <span>{disabledRowConfig.tip}</span>,
              }}
            </bk-popover>
          );
        }
        return props.multiple ? (
          <bk-checkbox
            style="vertical-align: middle;"
            model-value={Boolean(selectedMap.value[data.id])}
            label={true}
            onChange={(value: boolean) => handleSelecteRow(data, value)}
          />
          ) : (
          <bk-radio
            model-value={Boolean(selectedMap.value[data.id])}
            onChange={(value: boolean) => handleSelecteRow(data, value)}
            label={true}/>
        );
      },
    },
    {
      label: t('访问入口'),
      field: 'master_domain',
      width: 280,
      fixed: 'left',
      showOverflowTooltip: true,
      render: ({ data }: { data: ResourceItem }) => (
        <div class="cluster-name-box">
            <div class="cluster-name">{data.master_domain}</div>
            {
              !data.isOnline && (
                <bk-tag
                  class="ml-8"
                  size="small">
                  {t('已禁用')}
                </bk-tag>
              )
            }
            {
              data.operations && data.operations.length > 0 && (
                <bk-popover
                  theme="light"
                  width="360">
                  {{
                    default: () => <bk-tag theme="info" class="tag-box">{data.operations.length}</bk-tag>,
                    content: () => <ClusterRelatedTasks data={data.operations} />,
                  }}
                </bk-popover>
              )
            }
        </div>
      ),
    },
    {
      label: t('状态'),
      field: 'status',
      width: 90,
      filter: {
        list: [
          {
            value: 'normal',
            text: t('正常'),
          },
          {
            value: 'abnormal',
            text: t('异常'),
          },
        ],
        checked: columnCheckedMap.value.status,
      },
      render: ({ data }: { data: ResourceItem }) => {
        const isNormal = props.columnStatusFilter ? props.columnStatusFilter(data) : data.status === 'normal';
        const info = isNormal ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      width: 200,
      showOverflowTooltip: true,
    },
    {
      label: t('所属模块'),
      field: 'db_module_id',
      width: 150,
      showOverflowTooltip: true,
      filter: {
        list: columnAttrs.value.db_module_id,
        checked: columnCheckedMap.value.db_module_id,
      },
      render: ({ data }: { data: ResourceItem }) => <span>{data.db_module_name || '--'}</span>,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      width: 120,
      showOverflowTooltip: true,
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: { data: ResourceItem }) => <span>{data.bk_cloud_name}</span>,
    },
    {
      label: t('版本'),
      field: 'major_version',
      width: 200,
      showOverflowTooltip: true,
      render: ({ data }: { data: ResourceItem }) => data.major_version || '--',
    },
    {
      label: t('同步模式'),
      field: 'sync_mode',
      minWidth: 120,
      width: 120,
      render: ({ data }: { data: ResourceItem }) => <span>{data.sync_mode || '--'}</span>,
    },
  ]);

  const isIndeterminate = computed(() => !isSelectedAll.value && selectedList.value.length > 0);

  const mainSelectDisable = computed(() => tableData.value.filter(data => props.disabledRowConfig
    .find(item => item.handler(data))).length === tableData.value.length);

  const generatedColumns = computed(() => {
    if (props.customColums) {
      return [columns.value[0], ...props.customColums];
    }
    return columns.value;
  });

  watch(() => [props.activeTab, props.selected], () => {
    if (props.activeTab) {
      activeTab.value = props.activeTab;
      selectedList.value = props.selected;
      checkSelectedAll();
    }
  }, {
    immediate: true,
    deep: true,
  });

  watch(() => activeTab.value, () => {
    if (activeTab.value) {
      searchSelectValue.value = [];
    }
  });

  watch(isLoading, (status) => {
    if (!status) {
      checkSelectedAll();
    }
  });

  // 跨页全选
  const handleWholeSelect = () => {
    isLoading.value = true;
    props.getResourceList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      offset: 0,
      limit: -1,
      ...getSearchSelectorParams(searchValue.value),
    }).then((data) => {
      data.results.forEach((dataItem) => {
        if (!props.disabledRowConfig.find(item => item.handler(dataItem))) {
          handleSelecteRow(dataItem, true);
        }
      });
    }).finally(() => isLoading.value = false);
  };

  /**
   * 全选当页数据
   */
  const handleSelecteAll = (value: boolean) => {
    for (const data of tableData.value) {
      if (!props.disabledRowConfig.find(item => item.handler(data))) {
        handleSelecteRow(data, value);
      }
    }
  };

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

  const handleRowClick = (_: any, data: ResourceItem) => {
    if (props.disabledRowConfig.find(item => item.handler(data))) {
      return;
    }

    const isChecked = !!selectedMap.value[data.id];
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
        color: #3a84ff;
        border-radius: 8px !important;
      }
    }
  }
</style>
