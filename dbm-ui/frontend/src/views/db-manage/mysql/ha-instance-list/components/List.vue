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

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { type ClusterInstStatus, clusterInstStatus, ClusterTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams, isRecentDays } from '@utils';

  interface ColumnData {
    cell: string;
    data: TendbhaInstanceModel;
  }

  const instanceData = defineModel<{ clusterId: number; instanceAddress: string }>('instanceData');

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value.fetchData(params, { ...sortValue }, loading);
    isInit = false;
  };

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['role'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(isInit),
    isCluster: false,
    searchType: ClusterTypes.TENDBHA,
  });

  const searchSelectData = computed(() => [
    {
      id: 'instance',
      multiple: true,
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'domain',
      multiple: true,
      name: t('访问入口'),
    },
    {
      id: 'name',
      name: t('集群名称'),
    },
    {
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
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      children: searchAttrs.value.role,
      id: 'role',
      multiple: true,
      name: t('部署角色'),
    },
    {
      id: 'port',
      name: t('端口'),
    },
  ]);

  const tableRef = ref();

  const columns = computed(() => {
    const list = [
      {
        field: 'id',
        fixed: 'left',
        label: 'ID',
        width: 80,
      },
      {
        field: 'instance_address',
        fixed: 'left',
        label: t('实例'),
        minWidth: 200,
        render: ({ cell, data }: ColumnData) => (
          <TextOverflowLayout>
            {{
              append: () =>
                isRecentDays(data.create_at, 24 * 3) && (
                  <span
                    class='glob-new-tag ml-4'
                    data-text='NEW'
                  />
                ),
              default: () => (
                <auth-button
                  action-id='mysql_view'
                  permission={data.permission.mysql_view}
                  resource={data.cluster_id}
                  theme='primary'
                  text
                  onClick={() => handleToDetails(data)}>
                  {cell}
                </auth-button>
              ),
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'status',
        filter: {
          checked: columnCheckedMap.value.status,
          list: [
            {
              text: t('正常'),
              value: 'running',
            },
            {
              text: t('异常'),
              value: 'unavailable',
            },
            {
              text: t('重建中'),
              value: 'restoring',
            },
          ],
        },
        label: t('状态'),
        render: ({ cell }: { cell: ClusterInstStatus }) => {
          const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
          return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
        },
        width: 140,
      },
      {
        field: 'role',
        filter: {
          checked: columnCheckedMap.value.role,
          list: columnAttrs.value.role,
        },
        label: t('部署角色'),
        width: 140,
      },
      {
        field: 'bk_sub_zone',
        label: t('所在园区'),
        render: ({ cell }: ColumnData) => cell || '--',
        width: 140,
      },
      {
        field: 'master_domain',
        label: t('所属集群'),
        minWidth: 260,
        render: ({ cell }: ColumnData) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制所属集群')}
                  class='copy-btn'
                  type='copy'
                  onClick={() => execCopy(cell, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => cell,
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'cluster_name',
        label: t('集群名称'),
        minWidth: 180,
        render: ({ cell, data }: ColumnData) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  class='copy-btn'
                  type='copy'
                  onClick={() => execCopy(cell, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => (
                <auth-button
                  action-id='mysql_view'
                  permission={data.permission.mysql_view}
                  resource={data.cluster_id}
                  theme='primary'
                  text
                  onClick={() => handleToClusterDetails(data)}>
                  {cell}
                </auth-button>
              ),
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'create_at',
        label: t('部署时间'),
        render: ({ data }: { data: TendbhaInstanceModel }) => data.createAtDisplay || '--',
        sort: true,
        width: 240,
      },
      {
        fixed: 'right',
        label: t('操作'),
        render: ({ data }: { data: TendbhaInstanceModel }) => (
          <auth-button
            action-id='mysql_view'
            permission={data.permission.mysql_view}
            resource={data.cluster_id}
            theme='primary'
            text
            onClick={() => handleToDetails(data)}>
            {t('查看详情')}
          </auth-button>
        ),
        width: 100,
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
      row.cluster_id === instanceData.value?.clusterId &&
      row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter((cls) => cls).join(' ');
  };

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: columns.value.map((item) => item.field).filter((key) => !!key) as string[],
    fields: columns.value
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['instance_address', 'master_domain'].includes(item.field as string),
        field: item.field,
        label: item.label,
      })),
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.TENDBHA_INSTANCE_SETTINGS,
    defaultSettings,
  );

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
      clusterId: data.cluster_id,
      instanceAddress: data.instance_address,
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
