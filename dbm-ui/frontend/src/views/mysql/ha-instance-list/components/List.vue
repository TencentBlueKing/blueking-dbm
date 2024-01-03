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
  <div class="mysql-ha-instance-list-page">
    <div class="operation-box">
      <BkButton
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ t('实例申请') }}
      </BkButton>
      <DropdownExportExcel
        export-type="instance"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="tendbha" />
      <DbSearchSelect
        v-model="state.filters"
        class="mb-16"
        :data="searchSelectData"
        :placeholder="t('实例_域名_IP_端口_状态')"
        unique-select
        @change="handleChangeValues" />
    </div>
    <div
      v-bkloading="{ loading: state.isLoading }"
      class="table-wrapper"
      :class="{'is-shrink-table': isStretchLayoutOpen}">
      <DbOriginalTable
        :columns="columns"
        :data="state.data"
        :is-anomalies="isAnomalies"
        :is-searching="state.filters.length > 0"
        :pagination="renderPagination"
        remote-pagination
        :row-class="setRowClass"
        :settings="settings"
        @clear-search="handleClearSearch"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResourceInstances"
        @select-all="handleTableSelectedAll"
        @selection-change="handleTableSelected"
        @setting-change="updateTableSettings" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getTendbhaInstanceList } from '@services/source/tendbha';
  import type { ResourceInstance } from '@services/types';

  import {
    type IPagination,
    useCopy,
    useDefaultPagination,
    useStretchLayout,
    useTableSettings  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    ClusterTypes,
    DBTypes,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';

  import {
    getSearchSelectorParams,
    isRecentDays,
    utcDisplayTime,
  } from '@utils';

  interface ColumnData {
    cell: string,
    data: ResourceInstance
  }

  interface State {
    isLoading: boolean,
    data: Array<ResourceInstance>,
    pagination: IPagination,
    filters: Array<any>,
    selected: ResourceInstance[],
  }

  const instanceData = defineModel<{instanceAddress: string, clusterId: number}>('instanceData');

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const searchSelectData = [
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('实例'),
      id: 'instance_address',
    },
    {
      name: t('域名'),
      id: 'domain',
    },
    {
      name: 'IP',
      id: 'ip',
    },
    {
      name: t('端口'),
      id: 'port',
    },
    {
      name: t('状态'),
      id: 'status',
      children: Object.values(clusterInstStatus).map(item => ({ id: item.key, name: item.text })),
    },
  ];
  const state = reactive<State>({
    isLoading: false,
    data: [] as ResourceInstance[],
    pagination: useDefaultPagination(),
    filters: [],
    selected: [],
  });
  const isAnomalies = ref(false);

  const hasSelected = computed(() => state.selected.length > 0);
  const selectedIds = computed(() => state.selected.map(item => item.bk_host_id));

  const columns = computed(() => {
    const list = [
      {
        type: 'selection',
        width: 54,
        minWidth: 54,
        label: '',
        fixed: 'left',
      },
      {
        label: t('实例'),
        field: 'instance_address',
        fixed: 'left',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
        <div style="display: flex; align-items: center;">
          <div class="text-overflow" v-overflow-tips>
            <bk-button
              text
              theme="primary"
              onClick={() => handleToDetails(data)}>
              {cell}
            </bk-button>
          </div>
          {
            isRecentDays(data.create_at, 24 * 3)
            && <span class="glob-new-tag ml-4" data-text="NEW" />
          }
        </div>
      ),
      },
      {
        label: t('集群名称'),
        field: 'cluster_name',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
        <div class="domain">
          <bk-button
            v-overflow-tips
            class="text-overflow"
            text
            theme="primary"
            onClick={() => handleToClusterDetails(data)}>
            {cell}
          </bk-button>
          <db-icon
            v-bk-tooltips={t('复制集群名称')}
            type="copy"
            onClick={() => copy(cell)} />
        </div>
      ),
      },
      {
        label: t('状态'),
        field: 'status',
        width: 140,
        render: ({ cell }: { cell: ClusterInstStatus }) => {
          const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        label: t('主访问入口'),
        field: 'master_domain',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell }: ColumnData) => (
        <div class="domain">
          <span
            class="text-overflow"
            v-overflow-tips>
            {cell}
          </span>
          <db-icon
            v-bk-tooltips={t('复制主访问入口')}
            type="copy"
            onClick={() => copy(cell)} />
        </div>
      ),
      },
      {
        label: t('从访问入口'),
        field: 'slave_domain',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell }: ColumnData) => (
          <div class="domain">
            <span class="text-overflow" v-overflow-tips>
              {cell}
            </span>
            <db-icon
              type="copy"
              v-bk-tooltips={t('复制从访问入口')}
              onClick={() => copy(cell)} />
          </div>
        ),
      },
      {
        label: t('部署角色'),
        field: 'role',
      },
      {
        label: t('部署时间'),
        field: 'create_at',
        width: 160,
        render: ({ cell }: ColumnData) => <span>{utcDisplayTime(cell)}</span>,
      },
      {
        label: t('操作'),
        field: '',
        fixed: 'right',
        width: 140,
        render: ({ data }: { data: ResourceInstance }) => (
          <bk-button
            theme="primary"
            text
            onClick={() => handleToDetails(data)}>
            { t('查看详情') }
          </bk-button>
        ),
      },
    ];

    if (isStretchLayoutOpen.value) {
      list.pop();
    }

    return list;
  });

  // 设置行样式
  const setRowClass = (row: ResourceInstance) => {
    const classList = [isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId
      && row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter(cls => cls).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['instance_address', 'master_domain'].includes(item.field as string),
    })),
    checked: columns.value.map(item => item.field).filter(key => !!key) as string[],
    showLineHeight: false,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBHA_INSTANCE_SETTINGS, defaultSettings);

  const renderPagination = computed(() => {
    if (state.pagination.count < 10) {
      return false;
    }
    if (!isStretchLayoutOpen.value) {
      return { ...state.pagination };
    }
    return {
      ...state.pagination,
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });

  /**
    * 获取实例列表
    */
  fetchResourceInstances();
  function fetchResourceInstances() {
    state.isLoading = true;
    const params = {
      db_type: DBTypes.MYSQL,
      bk_biz_id: globalBizsStore.currentBizId,
      type: ClusterTypes.TENDBHA,
      ...state.pagination.getFetchParams(),
      ...getSearchSelectorParams(state.filters),
    };
    getTendbhaInstanceList(params)
      .then((res) => {
        state.pagination.count = res.count;
        state.data = res.results;
        isAnomalies.value = false;
      })
      .catch(() => {
        state.pagination.count = 0;
        state.data = [];
        isAnomalies.value = true;
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  const handleTableSelected = ({ row, checked }: {row: ResourceInstance, checked: boolean}) => {
    // 单选 checkbox 选中
    if (checked) {
      const toggleIndex = state.selected.findIndex(item => item.id === row.id);
      if (toggleIndex === -1) {
        state.selected.push(row);
      }
      return;
    }

    // 单选 checkbox 取消选中
    const toggleIndex = state.selected.findIndex(item => item.id === row.id);
    if (toggleIndex > -1) {
      state.selected.splice(toggleIndex, 1);
    }
  };

  /**
   * 表格全选
   */
  const handleTableSelectedAll = ({ checked, data }: {checked: boolean, data: ResourceInstance[]}) => {
    state.selected = checked ? [...data] : [];
  };

  function handleClearSearch() {
    state.filters = [];
    handleChangePage(1);
  }

  function handleChangePage(value: number) {
    state.pagination.current = value;
    fetchResourceInstances();
  }

  function handeChangeLimit(value: number) {
    state.pagination.limit = value;
    handleChangePage(1);
  }

  /**
   * 按条件过滤
   */
  function handleChangeValues() {
    nextTick(() => {
      handleChangePage(1);
    });
  }

  /**
   * 查看实例详情
   */
  function handleToDetails(data: ResourceInstance) {
    stretchLayoutSplitScreen();
    instanceData.value = {
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
    };
  }

  /**
   * 查看集群详情
   */
  function handleToClusterDetails(data: ResourceInstance) {
    router.push({
      name: 'DatabaseTendbha',
      query: {
        cluster_id: data.cluster_id,
      },
    });
  }

  /**
   * 申请实例
   */
  function handleApply() {
    router.push({
      name: 'SelfServiceApplyHa',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .mysql-ha-instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .operation-box {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }

  :deep(.cell) {
    .domain {
      display: flex;
      align-items: center;

      .db-icon-copy {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }
  }

  :deep(tr:hover) {
    .db-icon-copy {
      display: inline-block !important;
    }
  }

  .table-wrapper {
    background-color: white;

    .bk-table {
      height: 100% !important;
    }

    :deep(.bk-table-body) {
      max-height: calc(100% - 100px);
    }
  }

  .is-shrink-table {
    :deep(.bk-table-body) {
      overflow: hidden auto;
    }
  }
</style>
