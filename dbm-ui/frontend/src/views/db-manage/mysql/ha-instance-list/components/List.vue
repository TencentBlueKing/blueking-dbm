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
      <AuthButton
        action-id="mysql_apply"
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DbSearchSelect
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="getTendbhaInstanceList"
      releate-url-query
      :row-class="setRowClass"
      :settings="settings"
      show-settings
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @setting-change="updateTableSettings" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { getTendbhaInstanceList } from '@services/source/tendbha';

  import {
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    ClusterTypes,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import {
    execCopy,
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  interface ColumnData {
    cell: string,
    data: TendbhaInstanceModel
  }

  const instanceData = defineModel<{instanceAddress: string, clusterId: number}>('instanceData');

  let isInit = true;
  const fetchData = (loading?:boolean) => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData(params, { ...sortValue }, loading);
    isInit = false;
  };

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
  } = useStretchLayout();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBHA,
    attrs: ['role'],
    isCluster: false,
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const searchSelectData = computed(() => [
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
      multiple: true,
    },
    {
      name: t('访问入口'),
      id: 'domain',
      multiple: true,
    },
    {
      name: t('集群名称'),
      id: 'name',
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
      children: [
        {
          id: 'running',
          name: t('正常'),
        },
        {
          id: 'unavailable',
          name: t('异常'),
        },
        {
          id: 'loading',
          name: t('重建中'),
        },
      ],
    },
    {
      name: t('部署角色'),
      id: 'role',
      multiple: true,
      children: searchAttrs.value.role,
    },
    {
      name: t('端口'),
      id: 'port',
    },
  ]);

  const tableRef = ref();

  const columns = computed(() => {
    const list = [
      {
        label: 'ID',
        field: 'id',
        fixed: 'left',
        width: 80,
      },
      {
        label: t('实例'),
        field: 'instance_address',
        fixed: 'left',
        minWidth: 200,
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
          <TextOverflowLayout>
            {{
              default: () => (
                <auth-button
                  action-id="mysql_view"
                  resource={data.cluster_id}
                  permission={data.permission.mysql_view}
                  text
                  theme="primary"
                  onClick={() => handleToDetails(data)}>
                  {cell}
                </auth-button>
              ),
              append: () => isRecentDays(data.create_at, 24 * 3)
                && <span class="glob-new-tag ml-4" data-text="NEW" />,
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('状态'),
        field: 'status',
        width: 140,
        filter: {
          list: [
            {
              value: 'running',
              text: t('正常'),
            },
            {
              value: 'unavailable',
              text: t('异常'),
            },
            {
              value: 'restoring',
              text: t('重建中'),
            },
          ],
          checked: columnCheckedMap.value.status,
        },
        render: ({ cell }: { cell: ClusterInstStatus }) => {
          const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
      },
      {
        label: t('部署角色'),
        field: 'role',
        width: 140,
        filter: {
          list: columnAttrs.value.role,
          checked: columnCheckedMap.value.role,
        },
      },
      {
        label: t('所在园区'),
        field: 'bk_sub_zone',
        width: 140,
        render: ({ cell }: ColumnData) => cell || '--',
      },
      {
        label: t('所属集群'),
        field: 'master_domain',
        minWidth: 260,
        showOverflowTooltip: false,
        render: ({ cell }: ColumnData) => (
          <TextOverflowLayout>
            {{
              default: () => cell,
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制所属集群')}
                  type="copy"
                  class="copy-btn"
                  onClick={() => execCopy(cell, t('复制成功，共n条', { n: 1 }))} />
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('集群名称'),
        field: 'cluster_name',
        minWidth: 180,
        showOverflowTooltip: false,
        render: ({ cell, data }: ColumnData) => (
          <TextOverflowLayout>
            {{
              default: () => (
                <auth-button
                  action-id="mysql_view"
                  resource={data.cluster_id}
                  permission={data.permission.mysql_view}
                  text
                  theme="primary"
                  onClick={() => handleToClusterDetails(data)}>
                  {cell}
                </auth-button>
              ),
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  type="copy"
                  class="copy-btn"
                  onClick={() => execCopy(cell, t('复制成功，共n条', { n: 1 }))} />
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        label: t('部署时间'),
        field: 'create_at',
        width: 240,
        sort: true,
        render: ({ data }: { data: TendbhaInstanceModel }) => data.createAtDisplay || '--',
      },
      {
        label: t('操作'),
        fixed: 'right',
        width: 100,
        render: ({ data }: { data: TendbhaInstanceModel }) => (
          <auth-button
            action-id="mysql_view"
            permission={data.permission.mysql_view}
            resource={data.cluster_id}
            theme="primary"
            text
            onClick={() => handleToDetails(data)}>
            { t('查看详情') }
          </auth-button>
        ),
      },
    ];

    if (isStretchLayoutOpen.value) {
      list.pop();
    }

    return list;
  });

  // 设置行样式
  const setRowClass = (row: TendbhaInstanceModel) => {
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
    trigger: 'manual' as const,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBHA_INSTANCE_SETTINGS, defaultSettings);

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplyHa',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  };

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: TendbhaInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      instanceAddress: data.instance_address,
      clusterId: data.cluster_id,
    };
  };

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = (data: TendbhaInstanceModel) => {
    router.push({
      name: 'DatabaseTendbha',
      query: {
        id: data.cluster_id,
      },
    });
  };
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .mysql-ha-instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .vxe-cell {
      .copy-btn {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    tr:hover {
      .copy-btn {
        display: inline-block !important;
      }
    }

    .operation-box {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }
</style>
