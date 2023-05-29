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
  <div class="cluster-instances">
    <div class="cluster-instances__operations">
      <BkButton
        theme="primary"
        @click="handleApply">
        {{ $t('实例申请') }}
      </BkButton>
      <DbSearchSelect
        v-model="state.filters"
        :data="searchSelectData"
        :placeholder="$t('实例_域名_IP_端口_状态')"
        style="width: 320px;"
        unique-select
        @change="handleChangeValues" />
    </div>
    <BkLoading :loading="state.isLoading">
      <DbOriginalTable
        :columns="columns"
        :data="state.data"
        :is-anomalies="isAnomalies"
        :is-searching="state.filters.length > 0"
        :max-height="tableMaxHeight"
        :pagination="state.pagination"
        remote-pagination
        :row-class="setRowClass"
        :settings="settings"
        @clear-search="handleClearSearch"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage"
        @refresh="fetchResourceInstances"
        @setting-change="updateTableSettings" />
    </BkLoading>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getResourceInstances } from '@services/clusters';
  import type { ResourceInstance } from '@services/types/clusters';

  import {
    type IPagination,
    useCopy,
    useDefaultPagination,
    useTableMaxHeight,
    useTableSettings,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    ClusterTypes,
    DBTypes,
    OccupiedInnerHeight,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { getSearchSelectorParams, isRecentDays } from '@utils';

  interface ColumnData {
    cell: string,
    data: ResourceInstance
  }

  interface State {
    isLoading: boolean,
    data: Array<ResourceInstance>,
    pagination: IPagination,
    filters: Array<any>
  }

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.WITH_PAGINATION);

  const searchSelectData = [{
    name: t('实例'),
    id: 'instance_address',
  }, {
    name: t('域名'),
    id: 'domain',
  }, {
    name: 'IP',
    id: 'ip',
  }, {
    name: t('端口'),
    id: 'port',
  }, {
    name: t('状态'),
    id: 'status',
    children: Object.values(clusterInstStatus).map(item => ({ id: item.key, name: item.text })),
  }];
  const state = reactive<State>({
    isLoading: false,
    data: [] as ResourceInstance[],
    pagination: useDefaultPagination(),
    filters: [],
  });
  const isAnomalies = ref(false);

  const columns = [{
    label: t('实例'),
    field: 'instance_address',
    minWidth: 200,
    showOverflowTooltip: false,
    render: ({ cell, data }: ColumnData) => (
      <div style="display: flex; align-items: center;">
        <div class="text-overflow" v-overflow-tips>
          <a href="javascript:" onClick={() => handleToDetails(data)}>{cell}</a>
        </div>
        {
          isRecentDays(data.create_at, 24 * 3)
            ? <span class="glob-new-tag ml-4" data-text="NEW" />
            : null
        }
      </div>
    ),
  }, {
    label: t('集群名称'),
    field: 'cluster_name',
    minWidth: 200,
    showOverflowTooltip: false,
    render: ({ cell, data }: ColumnData) => (
      <div class="domain">
        <a class="text-overflow" href="javascript:" v-overflow-tips onClick={() => handleToClusterDetails(data)}>{cell}</a>
        <i class="db-icon-copy" v-bk-tooltips={t('复制集群名称')} onClick={() => copy(cell)} />
      </div>
    ),
  }, {
    label: t('状态'),
    field: 'status',
    width: 140,
    render: ({ cell }: { cell: ClusterInstStatus }) => {
      const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
      return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
    },
  }, {
    label: t('主域名'),
    field: 'master_domain',
    minWidth: 200,
    showOverflowTooltip: false,
    render: ({ cell }: ColumnData) => (
      <div class="domain">
        <span class="text-overflow" v-overflow-tips>{cell}</span>
        <i class="db-icon-copy" v-bk-tooltips={t('复制主域名')} onClick={() => copy(cell)} />
      </div>
    ),
  }, {
    label: t('从域名'),
    field: 'slave_domain',
    minWidth: 200,
    showOverflowTooltip: false,
    render: ({ cell }: ColumnData) => (
      <div class="domain">
        <span class="text-overflow" v-overflow-tips>{cell}</span>
        <i class="db-icon-copy" v-bk-tooltips={t('复制从域名')} onClick={() => copy(cell)} />
      </div>
    ),
  },  {
    label: t('部署角色'),
    field: 'role',
  }, {
    label: t('部署时间'),
    field: 'create_at',
    width: 160,
  }, {
    label: t('操作'),
    field: '',
    width: 140,
    render: ({ data }: { data: ResourceInstance }) => (
      <bk-button theme="primary" text onClick={handleToDetails.bind(this, data)}>{ t('查看详情') }</bk-button>
    ),
  }];
  // 设置行样式
  const setRowClass = (row: ResourceInstance) => (isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '');

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: ['instance_address', 'master_domain'].includes(item.field as string),
    })),
    checked: columns.map(item => item.field).filter(key => !!key) as string[],
    showLineHeight: false,
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBHA_INSTANCE_SETTINGS, defaultSettings);

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
    getResourceInstances(params)
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
    router.push({
      name: 'DatabaseTendbhaInstDetails',
      params: {
        address: data.instance_address,
        clusterId: data.cluster_id,
      },
    });
  }

  /**
   * 查看集群详情
   */
  function handleToClusterDetails(data: ResourceInstance) {
    router.push({
      name: 'DatabaseTendbhaDetails',
      params: {
        id: data.cluster_id,
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

  .cluster-instances {
    &__operations {
      margin-bottom: 16px;
      justify-content: space-between;
      .flex-center();
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
</style>
