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
  <div class="spider-list-instance-page">
    <div class="operation-box">
      <BkButton
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ $t('实例申请') }}
      </BkButton>
      <DbSearchSelect
        v-model="filterData"
        class="mb-16"
        :data="searchSelectData"
        :placeholder="$t('实例_域名_IP_端口_状态')"
        unique-select
        @change="fetchTableData" />
    </div>
    <div
      class="table-wrapper"
      :class="{'is-shrink-table': isStretchLayoutOpen}">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getResourceInstances"
        :pagination-extra="paginationExtra"
        :row-class="setRowClass"
        :settings="settings"
        @clear-search="handleClearSearch"
        @setting-change="updateTableSettings" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type TendbInstanceModel from '@services/model/spider/tendbInstance';
  import { getResourceInstances } from '@services/source/resourceSpider';

  import {
    useCopy,
    useStretchLayout,
    useTableSettings,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { getSearchSelectorParams, isRecentDays } from '@utils';

  import type { SearchSelectValues } from '@/types/bkui-vue';

  interface IColumn {
    cell: string,
    data: TendbInstanceModel
  }

  const instanceData = defineModel<{instanceAddress: string, clusterId: number}>('instanceData');

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const copy = useCopy();
  const { t } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const searchSelectData = [
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
  const tableRef = ref();
  const filterData = shallowRef<SearchSelectValues>([]);
  const paginationExtra = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return { small: false };
    }
    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });
  const columns = computed(() => {
    const list = [
      {
        label: t('实例'),
        field: 'instance_address',
        fixed: 'left',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: IColumn) => (
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
      },
      {
        label: t('集群名称'),
        field: 'cluster_name',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: IColumn) => (
          <div class="domain">
            <a
              class="text-overflow"
              href="javascript:"
              v-overflow-tips
              onClick={() => handleToClusterDetails(data)}>
              {cell}
            </a>
            <db-cion type="copy"
              v-bk-tooltips={t('复制集群名称')}
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
        render: ({ cell }: IColumn) => (
          <div class="domain">
            <span class="text-overflow" v-overflow-tips>{cell || '--'}</span>
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
        render: ({ cell }: IColumn) => (
          <div class="domain">
            <span
              class="text-overflow"
              v-overflow-tips>
              {cell || '--'}
            </span>
            {
              cell && (
                <db-icon
                  v-bk-tooltips={t('复制从访问入口')}
                  type="copy"
                  onClick={() => copy(cell)} />
              )
            }
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
      },
      {
        label: t('操作'),
        field: '',
        fixed: 'right',
        width: 140,
        render: ({ data }: { data: TendbInstanceModel }) => (
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
  const setRowClass = (row: TendbInstanceModel) => {
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
      label: item.label as string,
      field: item.field as string,
      disabled: ['instance_address', 'master_domain'].includes(item.field as string),
    })),
    checked: columns.value.map(item => item.field).filter(key => !!key) as string[],
    showLineHeight: false,
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBCLUSTER_INSTANCE_TABLE, defaultSettings);

  const fetchTableData = () => {
    tableRef.value.fetchData({
      ...getSearchSelectorParams(filterData.value),
    }, {});
  };

  // 清空搜索条件
  const handleClearSearch = () => {
    filterData.value = [];
    fetchTableData();
  };

  // 查看实例详情
  const handleToDetails = (data: TendbInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
    };
    console.log('go detail = ', instanceData.value);
  };

  // 查看集群详情
  const handleToClusterDetails = (data: TendbInstanceModel) => {
    router.push({
      name: 'tendbClusterList',
      query: {
        cluster_id: data.cluster_id,
      },
    });
  };

  // 申请实例
  const handleApply = () => {
    router.push({
      name: 'spiderApply',
      query: {
        bizId: currentBizId,
      },
    });
  };

  onMounted(() => {
    fetchTableData();
  });
</script>

<style lang="less">
  @import "@styles/mixins.less";

  .spider-list-instance-page {
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

    :deep(.table-wrapper) {
      background-color: white;

      .db-table,
      .bk-nested-loading {
        height: 100%;
      }

      .bk-table {
        height: 100% !important;
      }

      .bk-table-body {
        max-height: calc(100% - 100px);
      }
    }

    .is-shrink-table {
      :deep(.bk-table-body) {
        overflow: hidden auto;
      }
    }
  }
</style>
