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
      <AuthButton
        action-id="tendbcluster_apply"
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        export-type="instance"
        :ids="selectedIds"
        type="spider" />
      <DbSearchSelect
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div
      class="table-wrapper"
      :class="{ 'is-shrink-table': isStretchLayoutOpen }">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getTendbclusterInstanceList"
        :pagination-extra="paginationExtra"
        :row-class="setRowClass"
        selectable
        :settings="settings"
        show-settings
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type TendbInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { type ClusterInstStatus, clusterInstStatus, ClusterTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';

  import { execCopy, getSearchSelectorParams, isRecentDays, utcDisplayTime } from '@utils';

  interface IColumn {
    cell: string;
    data: TendbInstanceModel;
  }

  const instanceData = defineModel<{ clusterId: number; instanceAddress: string }>('instanceData');

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
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
    fetchDataFn: () => fetchTableData(),
    isCluster: false,
    searchType: ClusterTypes.TENDBCLUSTER,
  });

  const tableRef = ref();

  const selected = shallowRef<TendbInstanceModel[]>([]);

  const selectedIds = computed(() => selected.value.map((item) => item.bk_host_id));
  const paginationExtra = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return { small: false };
    }
    return {
      align: 'left',
      layout: ['total', 'limit', 'list'],
      small: true,
    };
  });
  const columns = computed(() => {
    const list = [
      {
        field: 'id',
        fixed: 'left',
        label: 'ID',
        width: 80,
      },
      {
        field: 'instance',
        fixed: 'left',
        label: t('实例'),
        render: ({ data }: IColumn) => (
          <TextOverflowLayout>
            {{
              append: () =>
                data.isNew && (
                  <span
                    class='glob-new-tag ml-4'
                    data-text='NEW'
                  />
                ),
              default: () => (
                <auth-button
                  action-id='tendbcluster_view'
                  permission={data.permission.tendbcluster_view}
                  resource={data.cluster_id}
                  theme='primary'
                  text
                  onClick={() => handleToDetails(data)}>
                  {data.instance_address}
                </auth-button>
              ),
            }}
          </TextOverflowLayout>
        ),
        width: 200,
      },
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
        render: ({ data }: IColumn) => data.bk_sub_zone || '--',
        width: 140,
      },
      {
        field: 'master_domain',
        label: t('所属集群'),
        minWidth: 260,
        render: ({ data }: { data: TendbInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () =>
                data.master_domain && (
                  <db-icon
                    v-bk-tooltips={t('复制所属集群')}
                    type='copy'
                    onClick={() => execCopy(data.master_domain, t('复制成功，共n条', { n: 1 }))}
                  />
                ),
              default: () => data.master_domain || '--',
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'cluster_name',
        label: t('集群名称'),
        minWidth: 180,
        render: ({ data }: { data: TendbInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  type='copy'
                  onClick={() => execCopy(data.cluster_name, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => (
                <router-link
                  to={{
                    name: 'tendbClusterList',
                    query: {
                      cluster_id: data.cluster_id,
                    },
                  }}
                  target='_blank'>
                  {data.cluster_name}
                </router-link>
              ),
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'create_at',
        label: t('部署时间'),
        render: ({ cell }: IColumn) => <span>{utcDisplayTime(cell)}</span>,
        sort: true,
        width: 240,
      },
      {
        field: '',
        fixed: 'right',
        label: t('操作'),
        render: ({ data }: { data: TendbInstanceModel }) => (
          <auth-button
            action-id='tendbcluster_view'
            permission={data.permission.tendbcluster_view}
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
      multiple: true,
      name: t('集群名称'),
    },
    {
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
        },
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      id: 'port',
      name: t('端口'),
    },
    {
      children: searchAttrs.value.role,
      id: 'role',
      multiple: true,
      name: t('部署角色'),
    },
  ]);

  // 设置行样式
  const setRowClass = (row: TendbInstanceModel) => {
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
        field: item.field as string,
        label: item.label as string,
      })),
    showLineHeight: false,
    trigger: 'manual' as const,
  };
  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.TENDBCLUSTER_INSTANCE_TABLE,
    defaultSettings,
  );

  const fetchTableData = () => {
    tableRef.value.fetchData(
      {
        ...getSearchSelectorParams(searchValue.value),
      },
      { ...sortValue },
    );
  };

  const handleSelection = (data: TendbInstanceModel, list: TendbInstanceModel[]) => {
    selected.value = list;
  };

  // 查看实例详情
  const handleToDetails = (data: TendbInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      clusterId: data.cluster_id,
      instanceAddress: data.instance_address,
    };
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
</script>

<style lang="less">
  @import '@styles/mixins.less';

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
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    tr:hover {
      .db-icon-copy {
        display: inline-block !important;
      }
    }

    .vxe-cell {
      .db-icon-copy {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }
  }
</style>
