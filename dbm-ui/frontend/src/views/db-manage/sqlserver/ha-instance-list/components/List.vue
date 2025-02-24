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
  <div class="sqlserver-ha-instance-list-page">
    <div class="operation-box">
      <BkButton
        class="mb-16"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </BkButton>
      <DropdownExportExcel
        export-type="instance"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="sqlserver_ha" />
      <DbSearchSelect
        class="mb-16"
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
        :data-source="getSqlServerInstanceList"
        releate-url-query
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

  import SqlServerHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
  import { getSqlServerInstanceList } from '@services/source/sqlserveHaCluster';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/index.vue';
  import MiniTag from '@components/mini-tag/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  const instanceData = defineModel<{
    clusterId: number;
    instanceAddress: string;
  }>('instanceData');

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
    searchType: ClusterTypes.SQLSERVER_HA,
  });

  const searchSelectData = computed(() => [
    {
      id: 'instance',
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

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const selected = shallowRef<SqlServerHaInstanceModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.id));

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
        render: ({ data }: { data: SqlServerHaInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <>
                  {data.isNew && (
                    <MiniTag
                      class='new-tag'
                      content='NEW'
                      theme='success'></MiniTag>
                  )}
                </>
              ),
              default: () => (
                <bk-button
                  theme='primary'
                  text
                  onClick={() => handleToDetails(data)}>
                  {data.instance_address}
                </bk-button>
              ),
            }}
          </TextOverflowLayout>
        ),
      },
      {
        field: 'cluster_name',
        label: t('集群名称'),
        minWidth: 200,
        render: ({ data }: { data: SqlServerHaInstanceModel }) => (
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
                <bk-button
                  theme='primary'
                  text
                  onClick={() => handleToClusterDetails(data)}>
                  {data.cluster_name}
                </bk-button>
              ),
            }}
          </TextOverflowLayout>
        ),
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
          ],
        },
        label: t('状态'),
        render: ({ data }: { data: SqlServerHaInstanceModel }) => {
          const { text, theme } = data.statusInfo;
          return <DbStatus theme={theme}>{text}</DbStatus>;
        },
        width: 140,
      },
      {
        field: 'master_domain',
        label: t('主访问入口'),
        minWidth: 200,
        render: ({ data }: { data: SqlServerHaInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制主访问入口')}
                  type='copy'
                  onClick={() => execCopy(data.master_domain, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => <span>{data.master_domain}</span>,
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'slave_domain',
        label: t('从访问入口'),
        minWidth: 200,
        render: ({ data }: { data: SqlServerHaInstanceModel }) => (
          <TextOverflowLayout>
            {{
              append: () => (
                <db-icon
                  v-bk-tooltips={t('复制从访问入口')}
                  type='copy'
                  onClick={() => execCopy(data.slave_domain, t('复制成功，共n条', { n: 1 }))}
                />
              ),
              default: () => <span>{data.slave_domain}</span>,
            }}
          </TextOverflowLayout>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'role',
        filter: {
          checked: columnCheckedMap.value.role,
          list: columnAttrs.value.role,
        },
        label: t('部署角色'),
      },
      {
        field: 'bk_sub_zone',
        label: t('所在园区'),
        render: ({ data }: { data: SqlServerHaInstanceModel }) => data.bk_sub_zone || '--',
        width: 140,
      },
      {
        field: 'create_at',
        label: t('部署时间'),
        render: ({ data }: { data: SqlServerHaInstanceModel }) => <span>{data.createAtDisplay}</span>,
        sort: true,
        width: 240,
      },
      {
        field: '',
        fixed: isStretchLayoutOpen.value ? false : 'right',
        label: t('操作'),
        render: ({ data }: { data: SqlServerHaInstanceModel }) => (
          <bk-button
            theme='primary'
            text
            onClick={() => handleToDetails(data)}>
            {t('查看详情')}
          </bk-button>
        ),
        width: 80,
      },
    ];

    if (isStretchLayoutOpen.value) {
      list.pop();
    }

    return list;
  });

  // 设置行样式
  const setRowClass = (row: SqlServerHaInstanceModel) => {
    const classList = [row.isNew ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId &&
      row.instance_address === instanceData.value?.instanceAddress
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
        disabled: ['instance_address', 'master_domain'].includes(item.field),
        field: item.field,
        label: item.label,
      })),
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.SQLSERVER_HA_INSTANCE_SETTINGS,
    defaultSettings,
  );

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value!.fetchData(
      {
        bk_biz_id: globalBizsStore.currentBizId,
        db_type: DBTypes.SQLSERVER,
        type: ClusterTypes.SQLSERVER_HA,
        ...getSearchSelectorParams(searchValue.value),
      },
      sortValue,
      loading,
    );
    isInit = false;
  };

  const handleSelection = (_key: any[], list: SqlServerHaInstanceModel[]) => {
    selected.value = list;
  };

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: SqlServerHaInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      clusterId: data.cluster_id,
      instanceAddress: data.instance_address,
    };
  };

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = (data: SqlServerHaInstanceModel) => {
    router.push({
      name: 'SqlServerHaClusterList',
      query: {
        cluster_id: data.cluster_id,
      },
    });
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceHaApply',
      query: {
        bizId: globalBizsStore.currentBizId,
      },
    });
  };
</script>

<style lang="less" scoped>
  .sqlserver-ha-instance-list-page {
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
  }

  :deep(.vxe-cell) {
    .db-icon-copy {
      display: none;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }

  :deep(tr:hover) {
    .db-icon-copy {
      display: inline-block !important;
    }
  }

  .table-wrapper {
    background-color: white;
  }
</style>
