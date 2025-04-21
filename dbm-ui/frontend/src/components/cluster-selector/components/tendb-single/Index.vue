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
    <DbOriginalTable
      class="table-box"
      :columns="generatedColumns"
      :data="tableData"
      :is-anomalies="isAnomalies"
      :is-searching="searchValue.length > 0"
      :max-height="528"
      :pagination="pagination.count < 10 ? false : pagination"
      remote-pagination
      :row-class="getRowClass"
      row-style="cursor: pointer"
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
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  import type { TabItem } from '../../Index.vue';
  import { tagsColumn } from '../common/columns';
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

  type ResourceItem = ValueOf<SelectedMap>[0];

  type Emits = (e: 'change', value: ResourceItem[]) => void;

  type SelectedMap = Props['selected'];

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    columnFilterChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id', 'db_module_id', 'major_version', 'region', 'time_zone'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    searchType: ClusterTypes.TENDBSINGLE,
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

  const columns = computed(() => [
    {
      fixed: 'left',
      label: () =>
        props.multiple && (
          <div style='display:flex;align-items:center'>
            <bk-checkbox
              key={`${pagination.current}_${activeTab.value}`}
              disabled={mainSelectDisable.value}
              indeterminate={isIndeterminate.value}
              label={true}
              model-value={isSelectedAll.value}
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
      minWidth: 70,
      render: ({ data }: { data: ResourceItem }) => {
        const disabledRowConfig = props.disabledRowConfig.find((item) => item.handler(data));
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
                    <bk-checkbox
                      style='vertical-align: middle;'
                      disabled
                    />
                  ) : (
                    <bk-radio
                      label={false}
                      disabled
                    />
                  ),
              }}
            </bk-popover>
          );
        }
        return props.multiple ? (
          <bk-checkbox
            label={true}
            model-value={Boolean(selectedMap.value[data.id])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleSelecteRow(data, value)}
            onClick={(e: Event) => e.stopPropagation()}
          />
        ) : (
          <bk-radio-group
            model-value={Boolean(selectedMap.value[data.id])}
            onChange={(value: boolean) => handleSelecteRow(data, value)}>
            <bk-radio label={true} />
          </bk-radio-group>
        );
      },
    },
    {
      field: 'master_domain',
      fixed: 'left',
      label: t('访问入口'),
      minWidth: 250,
      render: ({ data }: { data: ResourceItem }) => (
        <TextOverflowLayout class='cluster-name-box'>
          {{
            append: () => (
              <>
                {data.operations && data.operations.length > 0 && (
                  <bk-popover
                    theme='light'
                    width='360'>
                    {{
                      content: () => <ClusterRelatedTasks data={data.operations} />,
                      default: () => (
                        <bk-tag
                          class='tag-box'
                          theme='info'>
                          {data.operations.length}
                        </bk-tag>
                      ),
                    }}
                  </bk-popover>
                )}
                {data.isOffline && (
                  <bk-tag
                    class='ml-8'
                    size='small'>
                    {t('已禁用')}
                  </bk-tag>
                )}
              </>
            ),
            default: () => <span class='cluster-name'>{data.master_domain}</span>,
          }}
        </TextOverflowLayout>
      ),
      showOverflowTooltip: true,
    },
    tagsColumn,
    {
      field: 'status',
      filter: {
        checked: columnCheckedMap.value.status,
        list: [
          {
            text: t('正常'),
            value: 'normal',
          },
          {
            text: t('异常'),
            value: 'abnormal',
          },
        ],
      },
      label: t('状态'),
      minWidth: 100,
      render: ({ data }: { data: ResourceItem }) => {
        const isNormal = props.columnStatusFilter ? props.columnStatusFilter(data) : data.status === 'normal';
        const info = isNormal ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'cluster_name',
      label: t('集群名称'),
      minWidth: 120,
      showOverflowTooltip: true,
    },
    {
      field: 'masters',
      label: t('实例'),
      minWidth: 140,
      render: ({ data }: ResourceItem) => (
        <span>{data.masters.map((item: { ip: string; port: string }) => `${item.ip}:${item.port}`).join(',')}</span>
      ),
      showOverflowTooltip: true,
    },
    {
      field: 'db_module_id',
      filter: {
        checked: columnCheckedMap.value.db_module_id,
        list: columnAttrs.value.db_module_id,
      },
      label: t('所属模块'),
      minWidth: 100,
      render: ({ data }: { data: ResourceItem }) => <span>{data.db_module_name || '--'}</span>,
      showOverflowTooltip: true,
    },
    {
      field: 'bk_cloud_id',
      filter: {
        checked: columnCheckedMap.value.bk_cloud_id,
        list: columnAttrs.value.bk_cloud_id,
      },
      label: t('管控区域'),
      minWidth: 100,
      render: ({ data }: { data: ResourceItem }) => <span>{data.bk_cloud_name}</span>,
      showOverflowTooltip: true,
    },
  ]);

  const isIndeterminate = computed(() => !isSelectedAll.value && selectedList.value.length > 0);

  const mainSelectDisable = computed(
    () =>
      tableData.value.filter((data) => props.disabledRowConfig.find((item) => item.handler(data))).length ===
      tableData.value.length,
  );

  const generatedColumns = computed(() => {
    if (props.customColums) {
      return [columns.value[0], ...props.customColums];
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
        searchValue.value = [];
        handleTablePageChange(1);
      }
    },
  );

  watch(searchValue, () => {
    selectedList.value = [];
    emits('change', []);
  });

  const getRowClass = (data: ResourceItem) => data.isOffline && 'is-offline';

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
    if (value && !selectedMap.value[data.id]) {
      selectedList.value.push(data);
    } else {
      selectedList.value = selectedList.value.filter((item) => item.id !== data.id);
    }
    emits('change', selectedList.value);
    checkSelectedAll();
  };

  const handleRowClick = (_: any, data: ResourceItem) => {
    if (props.disabledRowConfig.find((item) => item.handler(data))) {
      return;
    }

    const isChecked = !!selectedMap.value[data.id];
    handleSelecteRow(data, !isChecked);
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
