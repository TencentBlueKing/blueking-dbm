<template>
  <div class="sqlserver-single-cluster-list">
    <div class="header-action">
      <div class="mb-16">
        <BkButton
          theme="primary"
          @click="handleApply">
          {{ t('申请实例') }}
        </BkButton>
        <BkDropdown
          class="ml-8"
          @hide="() => (isCopyDropdown = false)"
          @show="() => (isCopyDropdown = true)">
          <BkButton
            class="dropdown-button"
            :class="{ active: isCopyDropdown }">
            {{ t('复制') }}
            <DbIcon type="up-big dropdown-button-icon" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem>
                <BkButton
                  :disabled="tableDataList.length === 0"
                  text
                  @click="handleCopy(tableDataList)">
                  {{ t('所有集群 IP') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="selected.length === 0"
                  text
                  @click="handleCopy(selected)">
                  {{ t('已选集群 IP') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="abnormalDataList.length === 0"
                  text
                  @click="handleCopy(abnormalDataList)">
                  {{ t('异常集群 IP') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="tableDataList.length === 0"
                  text
                  @click="handleCopy(tableDataList, true)">
                  {{ t('所有集群实例') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="selected.length === 0"
                  text
                  @click="handleCopy(selected, true)">
                  {{ t('已选集群实例') }}
                </BkButton>
              </BkDropdownItem>
              <BkDropdownItem>
                <BkButton
                  :disabled="abnormalDataList.length === 0"
                  text
                  @click="handleCopy(abnormalDataList, true)">
                  {{ t('异常集群实例') }}
                </BkButton>
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
        <span
          v-bk-tooltips="{
            disabled: hasSelected,
            content: t('请选择集群'),
          }"
          class="inline-block">
          <BkButton
            class="ml-8"
            :disabled="!hasSelected"
            @click="handleShowAuthorize(selected)">
            {{ t('批量授权') }}
          </BkButton>
        </span>
        <BkButton
          class="ml-8"
          @click="handleShowExcelAuthorize">
          {{ t('导入授权') }}
        </BkButton>
        <DropdownExportExcel
          export-type="cluster"
          :has-selected="hasSelected"
          :ids="selectedIds"
          type="sqlserver_single" />
      </div>
      <DbSearchSelect
        class="header-select"
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <div class="table-wrapper">
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getSingleClusterList"
        releate-url-query
        :row-class="setRowClass"
        selectable
        :settings="settings"
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
    :cluster-types="[ClusterTypes.SQLSERVER_SINGLE]"
    :selected="authorizeSelected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
    :ticket-type="TicketTypes.SQLSERVER_EXCEL_AUTHORIZE_RULES" />
  <ClusterReset
    v-if="currentData"
    v-model:is-show="isShowClusterReset"
    :data="currentData"></ClusterReset>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';
  import {
    getSingleClusterList,
    getSqlServerInstanceList,
  } from '@services/source/sqlserverSingleCluster';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import {
    useCopy,
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage,
  } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import ClusterAuthorize from '@components/cluster-authorize/ClusterAuthorize.vue';
  import ClusterCapacityUsageRate from '@components/cluster-capacity-usage-rate/Index.vue'
  import ExcelAuthorize from '@components/cluster-common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@components/cluster-common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@components/cluster-common/RenderOperationTagNew.vue';
  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import DbTable from '@components/db-table/index.vue';
  import DropdownExportExcel from '@components/dropdown-export-excel/index.vue';
  import RenderInstances from '@components/render-instances/RenderInstances.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterReset from '@views/sqlserver-manage/components/cluster-reset/Index.vue'

  import {
    getMenuListSearch,
    getSearchSelectorParams,
  } from '@utils';

  import type {
    SearchSelectData,
    SearchSelectItem,
  } from '@/types/bkui-vue';

  const singleClusterData = defineModel<{ clusterId: number }>('singleClusterData');

  const router = useRouter();
  const route = useRoute();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const copy = useCopy();

  const {
    t,
    locale,
  } = useI18n();

  const {
    isOpen: isStretchLayoutOpen,
    splitScreen: stretchLayoutSplitScreen,
    handleOpenChange,
  } = useStretchLayout();

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
  } = useLinkQueryColumnSerach(ClusterTypes.SQLSERVER_SINGLE, [
    'bk_cloud_id',
    'db_module_id',
    'major_version',
    'region',
    'time_zone',
  ], () => fetchData(isInit));

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isCopyDropdown = ref(false);
  const selected = ref<SqlServerSingleClusterModel[]>([]);
  const isShowExcelAuthorize = ref(false);
  const isShowClusterReset = ref(false)
  const currentData = ref<SqlServerSingleClusterModel>()

  /** 集群授权 */
  const authorizeShow = ref(false);

  const authorizeSelected = ref<{
    master_domain: string,
    cluster_name: string,
    db_module_name: string,
  }[]>([]);

  const tableDataList = computed(() => tableRef.value!.getData<SqlServerSingleClusterModel>());
  const abnormalDataList = computed(() => tableDataList.value.filter(dataItem => dataItem.isAbnormal));
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
  const isCN = computed(() => locale.value === 'zh-cn');

  const searchSelectData = computed(() => [
    {
      name: t('IP 或 IP:Port'),
      id: 'instance',
    },
    {
      name: t('访问入口'),
      id: 'domain',
    },
    {
      name: 'ID',
      id: 'id',
    },
    {
      name: t('集群名称'),
      id: 'name',
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
      name: t('模块'),
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
  ] as SearchSelectData);

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 150 : 200;
    }
    return 100;
  });

  const columns = computed(() => [
    {
      label: 'ID',
      field: 'id',
      fixed: 'left',
      width: 100,
    },
    {
      label: t('访问入口'),
      field: 'master_domain',
      fixed: 'left',
      width: 200,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="sqlserver_view"
                resource={data.id}
                permission={data.permission.sqlserver_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data)}>
                {data.master_domain}
              </auth-button>
            ),
            append: () => (
              <>
                <div class="cluster-tags">
                  {
                    data.operationTagTips.map(item => (
                      <RenderOperationTag
                        class="cluster-tag ml-4"
                        data={item} />
                    ))
                  }
                </div>
                <div style="display: flex; align-items: center;">
                  <db-icon
                    type="copy"
                    v-bk-tooltips={ t('复制主访问入口') }
                    onClick={ () => copy(data.master_domain) } />
                  {/* <db-icon
                    type="link"
                    v-bk-tooltips={ t('新开tab打开') }
                    onClick={ () => handleToDetails(data, true) }/> */}
                  <div
                    class="text-overflow"
                    v-overflow-tips>
                    {
                      data.isNew && (
                        <span
                          class="glob-new-tag cluster-tag ml-4"
                          data-text="NEW" />
                      )
                    }
                  </div>
                </div>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      field: 'cluster_name',
      minWidth: 300,
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      width: 90,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.bk_cloud_name || '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      minWidth: 100,
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
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('实例'),
      field: 'storages',
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.storages}
          dataSource={getSqlServerInstanceList}
          title={t('【inst】实例预览', { inst: data.bk_cloud_name })}
          role="storages"
          clusterId={data.id}
        />
      )
    },
    {
      label: t('所属DB模块'),
      field: 'db_module_id',
      width: 140,
      showOverflowTooltip: true,
      filter: {
        list: columnAttrs.value.db_module_id,
        checked: columnCheckedMap.value.db_module_id,
      },
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.db_module_name || '--'}</span>,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.major_version || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.region || '--'}</span>,
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 160,
      sort: true,
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
      render: ({ data }: { data: SqlServerSingleClusterModel }) => <span>{data.cluster_time_zone || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      width: tableOperationWidth.value,
      fixed: 'right',
      render: ({ data }: { data: SqlServerSingleClusterModel }) => (
        <>
          {
            data.isOnline ? (
              <>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    onClick={ () => handleShowAuthorize([data]) }>
                    { t('授权') }
                  </bk-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    class="ml-16"
                    disabled={data.operationDisabled}
                    onClick={ () => handleSwitchCluster(TicketTypes.SQLSERVER_DISABLE, data) }>
                    { t('禁用') }
                </bk-button>
                </OperationBtnStatusTips>
              </>
            ) : (
              <>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    disabled={data.isStarting}
                    onClick={ () => handleSwitchCluster(TicketTypes.SQLSERVER_ENABLE, data) }>
                    { t('启用') }
                  </bk-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    class="ml-16"
                    disabled={Boolean(data.operationTicketId)}
                    onClick={() => handleResetCluster(data)}>
                    { t('重置') }
                  </bk-button>
                </OperationBtnStatusTips>
                <OperationBtnStatusTips data={ data }>
                  <bk-button
                    text
                    theme="primary"
                    class="ml-16"
                    disabled={Boolean(data.operationTicketId)}
                    onClick={ () => handleDeleteCluster(data) }>
                    { t('删除') }
                  </bk-button>
                </OperationBtnStatusTips>
              </>
            )
          }
        </>
      ),
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field ,
      disabled: ['master_domain'].includes(item.field as string),
    })),
    checked: (columns.value || []).map(item => item.field).filter(key => !!key && key !== 'id'),
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.SQLSERVER_SINGLE_TABLE_SETTINGS, defaultSettings);

  const { run: createTicketRun } = useRequest(createTicket, {
    manual: true,
    onSuccess(res) {
      ticketMessage(res.id);
    },
  });

  const getMenuList = async (item: SearchSelectItem | undefined, keyword: string) => {
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

  /**
   * 集群启停
   */
  const handleSwitchCluster = (
    type: TicketTypesStrings,
    data: SqlServerSingleClusterModel,
  ) => {
    if (!type) return;

    const isOpen = type === TicketTypes.SQLSERVER_ENABLE;
    InfoBox({
      type: 'warning',
      title: isOpen ? t('确定启用该集群？') : t('确定禁用该集群？'),
      content: () => (
        <div style="word-break: all;">
          <p style="color: #313238">{t('集群')} ：{data.cluster_name}</p>
          {
            isOpen
              ? <p>{ t('启用后将恢复访问')}</p>
              : <p>{ t('被禁用后将无法访问，如需恢复访问，可以再次「启用」')}</p>
          }
        </div>
      ),
      confirmText: isOpen ? t('启用') : t('禁用'),
      onConfirm: () => {
        createTicketRun({
          bk_biz_id: currentBizId,
          ticket_type: type,
          details: {
            cluster_ids: [data.id],
          },
        });
        return true;
      },
    });
  };

  /**
   * 删除集群
   */
  const handleDeleteCluster = (data: SqlServerSingleClusterModel) => {
    const { cluster_name: name } = data;
    InfoBox({
      type: 'warning',
      title: t('确定删除该集群'),
      confirmText: t('删除'),
      confirmButtonTheme: 'danger',
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{ t('集群【name】被删除后_将进行以下操作', { name }) }</p>
          <p>{ t('1_删除xx集群', { name }) }</p>
          <p>{ t('2_删除xx实例数据_停止相关进程', { name }) }</p>
          <p>3. { t('回收主机') }</p>
        </div>
      ),
      onConfirm: () => {
        createTicketRun({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.SQLSERVER_DESTROY,
          details: {
            cluster_ids: [data.id],
          },
        });
        return false;
      },
    });
  };

  const handleResetCluster = (data: SqlServerSingleClusterModel) => {
    currentData.value = data
    isShowClusterReset.value = true
  }

  // excel 授权
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value!.fetchData(
      { ...getSearchSelectorParams(searchValue.value) },
      { bk_biz_id: window.PROJECT_CONFIG.BIZ_ID, ...sortValue },
      loading
    );
    isInit = false;
  };

  const handleCopy = (dataList: SqlServerSingleClusterModel[], isInstance = false) => {
    const list = dataList.reduce((prevList, tableItem) => {
      const storageList = tableItem.storages.map(storageItem => (isInstance ? `${storageItem.ip}:${storageItem.port}` : `${storageItem.ip}`));
      return [...prevList, ...storageList];
    }, [] as string[]);
    copy(list.join('\n'));
  };

  // 设置行样式
  const setRowClass = (row: SqlServerSingleClusterModel) => {
    const classStack = [];
    if (row.isNew) {
      classStack.push('is-new-row');
    }
    if (singleClusterData.value && row.id === singleClusterData.value.clusterId) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  const handleSelection = (key: number[], list: Record<number, SqlServerSingleClusterModel>[]) => {
    selected.value = list as unknown as SqlServerSingleClusterModel[];
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
   * 查看详情
   */
  const handleToDetails = (
    data: SqlServerSingleClusterModel,
    isAllSpread: boolean = false,
  ) => {
    stretchLayoutSplitScreen();
    singleClusterData.value = { clusterId: data.id };
    if (isAllSpread) {
      handleOpenChange('left');
    }
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SqlServiceSingleApply',
      query: {
        bizId: currentBizId,
        from: String(route.name),
      },
    });
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .sqlserver-single-cluster-list {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .header-select {
        flex: 1;
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    :deep(.cell) {
      line-height: normal !important;

      .domain {
        display: flex;
        align-items: center;
      }

      .db-icon-copy,
      .db-icon-link {
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

    :deep(tr:hover) {
      .db-icon-copy,
      .db-icon-link {
        display: inline-block !important;
      }
    }
  }
</style>
