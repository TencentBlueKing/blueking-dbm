<template>
  <div class="sqlserver-ha-cluster-list">
    <div class="header-action">
      <div class="mb-16">
        <BkButton
          v-db-console="'sqlserver.haClusterList.instanceApply'"
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </BkButton>
        <ClusterBatchOperation
          v-db-console="'sqlserver.haClusterList.batchOperation'"
          class="ml-8"
          :cluster-type="ClusterTypes.SQLSERVER_HA"
          :selected="selected"
          @success="handleBatchOperationSuccess" />
        <BkButton
          v-db-console="'sqlserver.haClusterList.importAuthorize'"
          class="ml-8"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
        <DropdownExportExcel
          v-db-console="'sqlserver.haClusterList.export'"
          export-type="cluster"
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="sqlserver_ha" />
        <ClusterIpCopy
          v-db-console="'sqlserver.haClusterList.batchCopy'"
          :selected="selected" />
      </div>
      <DbSearchSelect
        class="header-select mb-16"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
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
        :data-source="getHaClusterList"
        releate-url-query
        :row-class="setRowClass"
        selectable
        :settings="settings"
        :show-overflow="false"
        show-overflow-tips
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeShow"
    :account-type="AccountTypes.SQLSERVER"
    :cluster-types="[ClusterTypes.SQLSERVER_HA]"
    :selected="authorizeSelected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.SQLSERVER_HA"
    :ticket-type="TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES" />
  <ClusterReset
    v-if="currentData"
    v-model:is-show="isShowClusterReset"
    :data="currentData"></ClusterReset>
</template>
<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import {
    getHaClusterList,
    getSqlServerInstanceList,
  } from '@services/source/sqlserveHaCluster';
  import { getUserList } from '@services/source/user';

  import {
    useCopy,
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    DBTypes,
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import ClusterBatchOperation from '@views/db-manage/common/cluster-batch-opration/Index.vue'
  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue'
  import EditEntryConfig, { type ClusterEntryInfo } from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderInstances from '@views/db-manage/common/render-instances/RenderInstances.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';
  import ClusterReset from '@views/db-manage/sqlserver/components/cluster-reset/Index.vue'

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    // isRecentDays
  } from '@utils';

  const haClusterData = defineModel<{
    clusterId: number,
  }>('haClusterData');

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();

  const {
    t,
    locale,
  } = useI18n();

  const { handleDisableCluster, handleEnableCluster, handleDeleteCluster } = useOperateClusterBasic(
    ClusterTypes.SQLSERVER,
    {
      onSuccess: () => fetchData(),
    },
  );

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
    handleOpenChange,
  } = useStretchLayout();

  const copy = useCopy();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    sortValue,
    columnCheckedMap,
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.SQLSERVER_HA,
    attrs: [
      'bk_cloud_id',
      'db_module_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchData(isInit),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false)
  const currentData = ref<SqlServerHaModel>()
  const selected = ref<SqlServerHaModel[]>([])

  /** 集群授权 */
  const authorizeShow = ref(false);
  const authorizeSelected = ref<{
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isCN = computed(() => locale.value === 'zh-cn');

  const searchSelectData = computed(() => [
    {
      name: t('访问入口'),
      id: 'domain',
      multiple: true,
    },
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
      multiple: true,
    },
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名称'),
      id: 'name',
      multiple: true,
    },
    {
      name: t('管控区域'),
      id: 'bk_cloud_id',
      multiple: true,
      children: searchAttrs.value.bk_cloud_id,
    },
    {
      name: t('状态'),
      id: 'status',
      multiple: true,
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
    },
    {
      name: t('所属DB模块'),
      id: 'db_module_id',
      multiple: true,
      children: searchAttrs.value.db_module_id,
    },
    {
      name: t('版本'),
      id: 'major_version',
      multiple: true,
      children: searchAttrs.value.major_version,
    },
    {
      name: t('地域'),
      id: 'region',
      multiple: true,
      children: searchAttrs.value.region,
    },
    {
      name: t('创建人'),
      id: 'creator',
    },
    {
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);


  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 180 : 200;
    }
    return 100;
  });

  const entrySort = (data: ClusterEntryInfo[]) => data.sort(a => a.role === 'master_entry' ? -1 : 1);

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('主访问入口'),
      field: 'master_domain',
      fixed: 'left',
      minWidth: 280,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'master_domain',
                label: t('域名')
              },
              {
                field: 'masterDomainDisplayName',
                label: t('域名:端口')
              }
            ]
          }
        >
          {t('主访问入口')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: SqlServerHaModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="sqlserver_view"
                permission={data.permission.sqlserver_view}
                resource-id={data.id}
                text
                theme="primary"
                onClick={() => handleToDetails(data)}>
                {data.masterDomainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                {
                  data.operationTagTips.map(item => (
                    <RenderOperationTag
                      class="cluster-tag"
                      data={item} />
                  ))
                }
                {
                  data.isOffline && !data.isStarting && (
                    <bk-tag
                      class="ml-4"
                      size="small">
                      {t('已禁用')}
                    </bk-tag>
                  )
                }
                <RenderCellCopy copyItems={
                  [
                    {
                      value: data.master_domain,
                      label: t('域名')
                    },
                    {
                      value: data.masterDomainDisplayName,
                      label: t('域名:端口')
                    }
                  ]
                }/>
                {
                  data.isNew && (
                    <bk-tag
                      theme="success"
                      size="small"
                      class="ml-4">
                      NEW
                    </bk-tag>
                  )
                }
                <span v-db-console="sqlserver.haClusterList.modifyEntryConfiguration">
                  <EditEntryConfig
                    id={data.id}
                    bizId={data.bk_biz_id}
                    permission={data.permission.access_entry_edit}
                    resource={DBTypes.SQLSERVER}
                    sort={entrySort}
                    onSuccess={fetchData}>
                      {{
                        prepend: ({ data: cluster }: { data: ClusterEntryInfo } ) =>
                          cluster.role === 'master_entry' ?
                            <bk-tag size="small" theme="success">{ t('主') }</bk-tag>
                            : <bk-tag size="small" theme="info">{ t('从') }</bk-tag>,
                      }}
                  </EditEntryConfig>
                </span>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 200,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'cluster_name'
              },
            ]
          }
        >
          {t('集群名称')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: SqlServerHaModel }) => (
        <TextOverflowLayout>
          {{
            default: () => data.cluster_name,
            append: () => (
              <>
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  type="copy"
                  onClick={() => copy(data.cluster_name)} />
              </>
            ),
          }}
        </TextOverflowLayout>
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
      render: ({ data }: { data: SqlServerHaModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: { data: SqlServerHaModel }) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('从访问入口'),
      field: 'slave_domain',
      minWidth: 200,
      width: 220,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'slave_domain',
                label: t('域名')
              },
              {
                field: 'slaveDomainDisplayName',
                label: t('域名:端口')
              }
            ]
          }
        >
          {t('从访问入口')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: SqlServerHaModel }) => (
        <TextOverflowLayout>
          {{
            default: () => data.slaveDomainDisplayName || '--',
            append: () => (
              <>
                <RenderCellCopy copyItems={
                  [
                    {
                      value: data.slave_domain,
                      label: t('域名')
                    },
                    {
                      value: data.slaveDomainDisplayName,
                      label: t('域名:端口')
                    }
                  ]
                } />
                <span v-db-console="sqlserver.haClusterList.modifyEntryConfiguration">
                  <EditEntryConfig
                    id={data.id}
                    bizId={data.bk_biz_id}
                    permission={data.permission.access_entry_edit}
                    resource={DBTypes.TENDBCLUSTER}
                    sort={entrySort}
                    onSuccess={fetchData}>
                      {{
                        prepend: ({ data: cluster }: { data: ClusterEntryInfo } ) =>
                          cluster.role === 'master_entry' ?
                            <bk-tag size="small" theme="success">{ t('主') }</bk-tag>
                            : <bk-tag size="small" theme="info">{ t('从') }</bk-tag>,
                      }}
                  </EditEntryConfig>
                </span>
              </>
            )
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: 'Master',
      field: 'masters',
      width: 200,
      minWidth: 200,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'masters')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'masters')}
          config={
            [
              {
                label: 'IP',
                field: 'ip'
              },
              {
                label: t('实例'),
                field: 'instance'
              }
            ]
          }
        >
          {'Master'}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: SqlServerHaModel }) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.masters}
          title={t('【inst】实例预览', { inst: data.bk_cloud_name, title: 'Master' })}
          role="backend_master"
          clusterId={data.id}
          dataSource={getSqlServerInstanceList} />
      ),
    },
    {
      label: 'Slave',
      field: 'slaves',
      width: 200,
      minWidth: 200,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'slaves')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'slaves')}
          config={
            [
              {
                label: 'IP',
                field: 'ip'
              },
              {
                label: t('实例'),
                field: 'instance'
              }
            ]
          }
        >
          {'Slave'}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: SqlServerHaModel }) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.slaves}
          title={t('【inst】实例预览', { inst: data.bk_cloud_name, title: 'Slaves' })}
          role="backend_slave"
          clusterId={data.id}
          dataSource={getSqlServerInstanceList} />
    ),
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_id',
      width: 140,
      filter: {
        list: columnAttrs.value.db_module_id,
        checked: columnCheckedMap.value.db_module_id,
      },
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.db_module_name || '--'}</span>,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 180,
      width: 180,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('同步模式'),
      field: 'sync_mode',
      minWidth: 120,
      width: 120,
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.sync_mode || '--'}</span>,
    },
    {
      label: t('容灾要求'),
      field: 'disaster_tolerance_level',
      minWidth: 100,
      render: ({ data }: { data: SqlServerHaModel }) => data.disasterToleranceLevelName || '--',
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.region || '--'}</span>,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      width: 90,
      render: ({ data }: { data: SqlServerHaModel }) =>  data.bk_cloud_name ? `${data.bk_cloud_name}[${data.bk_cloud_id}]` : '--',
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 200,
      sort: true,
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
      render: ({ data }: { data: SqlServerHaModel }) => <span>{data.cluster_time_zone || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: { data: SqlServerHaModel }) => {
        const oprations = []

        if (data.isOnline) {
          oprations.push([
            <bk-button
              v-db-console="sqlserver.haClusterList.authorize"
              text
              theme="primary"
              onClick={ () => handleShowAuthorize([data]) }>
              { t('授权') }
            </bk-button>,
            <OperationBtnStatusTips
              data={ data }
              v-db-console="sqlserver.haClusterList.disable">
              <bk-button
                text
                theme="primary"
                class="ml-16"
                disabled={data.operationDisabled}
                onClick={() => handleDisableCluster([data])}>
                { t('禁用') }
              </bk-button>
            </OperationBtnStatusTips>
          ])
        } else {
          oprations.push([
            <OperationBtnStatusTips
              data={ data }
              v-db-console="sqlserver.haClusterList.enable">
              <bk-button
                text
                theme="primary"
                disabled={data.isStarting}
                onClick={ () => handleEnableCluster([data]) }>
                { t('启用') }
              </bk-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips
              data={ data }
              v-db-console="sqlserver.haClusterList.reset">
              <bk-button
                text
                theme="primary"
                class="ml-16"
                disabled={Boolean(data.operationTicketId)}
                onClick={() => handleResetCluster(data)}>
                { t('重置') }
              </bk-button>
            </OperationBtnStatusTips>
          ])
        }

        oprations.push(
          <OperationBtnStatusTips
            data={ data }
            v-db-console="sqlserver.haClusterList.delete">
            <bk-button
              v-bk-tooltips={{
                disabled: data.isOffline,
                content: t('请先禁用集群')
              }}
              text
              theme="primary"
              class="ml-16"
              disabled={data.isOnline || Boolean(data.operationTicketId)}
              onClick={() => handleDeleteCluster(TicketTypes.SQLSERVER_DESTROY, [data])}>
              { t('删除') }
            </bk-button>
          </OperationBtnStatusTips>
        )

        return oprations
      }
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: columns.value.filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field ,
      disabled: ['master_domain'].includes(item.field as string),
    })),
    checked: [
      'master_domain',
      'status',
      'cluster_stats',
      'slave_domain',
      'masters',
      'slaves',
      'db_module_id',
      'major_version',
      'disaster_tolerance_level',
      'region',
      'spec_name',
    ],
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.SQLSERVER_HA_TABLE_SETTINGS, defaultSettings);

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return searchSelectData.value.filter(item => !selected.includes(item.id));
    }

    // 远程加载执行人
    if (item.id === 'creator') {
      if (!keyword) {
        return [];
      }
      return getUserList({
        fuzzy_lookups: keyword,
      }).then(res => res.results.map(item => ({
        id: item.username,
        name: item.username,
      })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value!.fetchData(
      { ...getSearchSelectorParams(searchValue.value) },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ...sortValue
      },
      loading
    );
    isInit = false;
  };

  const handleCopy = <T,>(dataList: T[], field: keyof T) => {
    const copyList = dataList.reduce((prevList, tableItem) => {
      const value = String(tableItem[field]);
      if (value && value !== '--' && !prevList.includes(value)) {
        prevList.push(value);
      }
      return prevList;
    }, [] as string[]);
    copy(copyList.join('\n'));
  }

  // 获取列表数据下的实例子列表
  const getInstanceListByRole = (dataList: SqlServerHaModel[], field: keyof SqlServerHaModel) => dataList.reduce((result, curRow) => {
    result.push(...curRow[field] as SqlServerHaModel['masters']);
    return result;
  }, [] as SqlServerHaModel['masters']);

  const handleCopySelected = <T,>(field: keyof T, role?: keyof SqlServerHaModel) => {
    if(role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field)
      return;
    }
    handleCopy(selected.value as T[], field)
  }

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof SqlServerHaModel) => {
    const allData = await tableRef.value!.getAllData<SqlServerHaModel>();
    if(allData.length === 0) {
      Message({
        theme: 'primary',
        message: t('暂无数据可复制'),
      });
      return;
    }
    if(role) {
      handleCopy(getInstanceListByRole(allData, role) as T[], field)
      return;
    }
    handleCopy(allData as T[], field)
  }

  const handleResetCluster = (data: SqlServerHaModel) => {
    currentData.value = data
    isShowClusterReset.value = true
  }

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  // 设置行样式
  const setRowClass = (row: SqlServerHaModel) => {
    const classStack = [];
    if (row.isNew) {
      classStack.push('is-new-row');
    }
    if (haClusterData.value && row.id === haClusterData.value.clusterId) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  /**
   * 查看详情
   */
  const handleToDetails = (
    data: SqlServerHaModel,
    isAllSpread = false,
  ) => {
    stretchLayoutSplitScreen();
    haClusterData.value = {
      clusterId: data.id,
    };
    if (isAllSpread) {
      handleOpenChange('left');
    }
  };

  const handleSelection = (key: number[], list: Record<number, SqlServerHaModel>[]) => {
    selected.value = list as unknown as SqlServerHaModel[];
  };

  const handleClearSelected = () => {
    selected.value = [];
    authorizeSelected.value = [];
  };

  const handleShowAuthorize = (selected: {
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]) => {
    authorizeShow.value = true;
    authorizeSelected.value = selected;
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceHaApply',
      query: {
        bizId: currentBizId,
        from: String(route.name),
      },
    });
  };

  const handleBatchOperationSuccess = () => {
    tableRef.value!.clearSelected();
    fetchData();
  }
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .sqlserver-ha-cluster-list {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .header-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    td .vxe-cell {
      .db-icon-copy,
      .db-icon-link,
      .db-icon-visible1 {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }

      .operations-more {
        .db-icon-more {
          display: block;
          font-size: @font-size-normal;
          font-weight: bold;
          color: @default-color;
          cursor: pointer;

          &:hover {
            background-color: @bg-disable;
            border-radius: 2px;
          }
        }
      }
    }

    th:hover,
    td:hover {
      .db-icon-copy,
      .db-icon-link,
      .db-icon-visible1 {
        display: inline-block !important;
      }
    }
  }
</style>
