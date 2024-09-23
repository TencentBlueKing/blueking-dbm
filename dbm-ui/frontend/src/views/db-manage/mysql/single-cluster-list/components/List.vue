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
  <div class="mysql-single-cluster-list-page">
    <div class="operation-box">
      <AuthButton
        v-db-console="'mysql.singleClusterList.instanceApply'"
        action-id="mysql_apply"
        theme="primary"
        @click="handleApply">
        {{ t('申请实例') }}
      </AuthButton>
      <span
        v-bk-tooltips="{
          disabled: hasSelected,
          content: t('请选择集群'),
        }"
        v-db-console="'mysql.singleClusterList.batchAuthorize'"
        class="inline-block">
        <BkButton
          class="ml-8"
          :disabled="!hasSelected"
          @click="handleShowAuthorize(selected)">
          {{ t('批量授权') }}
        </BkButton>
      </span>
      <BkButton
        v-db-console="'mysql.singleClusterList.importAuthorize'"
        class="ml-8"
        @click="handleShowExcelAuthorize">
        {{ t('导入授权') }}
      </BkButton>
      <DropdownExportExcel
        v-db-console="'mysql.singleClusterList.export'"
        :ids="selectedIds"
        type="tendbsingle" />
      <ClusterIpCopy
        v-db-console="'mysql.singleClusterList.batchCopy'"
        :selected="selected" />
      <DbSearchSelect
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
        :data-source="getTendbsingleList"
        releate-url-query
        :row-class="setRowClass"
        selectable
        :settings="settings"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
  </div>
  <!-- 集群授权 -->
  <ClusterAuthorize
    v-model="authorizeState.isShow"
    :account-type="AccountTypes.MYSQL"
    :cluster-types="[ClusterTypes.TENDBSINGLE]"
    :selected="authorizeState.selected"
    @success="handleClearSelected" />
  <!-- excel 导入授权 -->
  <ExcelAuthorize
    v-model:is-show="isShowExcelAuthorize"
    :cluster-type="ClusterTypes.TENDBSINGLE" />
  <ClusterExportData
    v-if="currentData"
    v-model:is-show="showDataExportSlider"
    :data="currentData"
    :ticket-type="TicketTypes.MYSQL_DUMP_DATA" />
</template>

<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import {
    useRoute,
    useRouter,
  } from 'vue-router';

  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import {
    getTendbsingleDetail,
    getTendbsingleInstanceList,
    getTendbsingleList,
  } from '@services/source/tendbsingle';
  import { createTicket } from '@services/source/ticket';
  import { getUserList } from '@services/source/user';

  import {
    useCopy,
    useLinkQueryColumnSerach,
    useStretchLayout,
    useTableSettings,
    useTicketMessage
  } from '@hooks';

  import {
    useGlobalBizs,
  } from '@stores';

  import {
    AccountTypes,
    ClusterTypes,
    DBTypes,
    TicketTypes,
    type TicketTypesStrings,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/index.vue';
  import MoreActionExtend from '@components/more-action-extend/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/ClusterAuthorize.vue';
  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue'
  import EditEntryConfig from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue'
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import ExcelAuthorize from '@views/db-manage/common/ExcelAuthorize.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderInstances from '@views/db-manage/common/render-instances/RenderInstances.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTag.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams,
    isRecentDays,
  } from '@utils';

  interface ColumnData {
    cell: string,
    data: TendbsingleModel
  }

  const clusterId = defineModel<number>('clusterId');

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const copy = useCopy();
  const { t, locale } = useI18n();
  const ticketMessage = useTicketMessage();
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
    batchSearchIpInatanceList,
    columnFilterChange,
    columnSortChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.TENDBSINGLE,
    attrs: [
      'bk_cloud_id',
      'db_module_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  });

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExcelAuthorize = ref(false);
  const showDataExportSlider = ref(false)
  const selected = ref<TendbsingleModel[]>([])
  const currentData = ref<ColumnData['data']>();

  const authorizeState = reactive({
    isShow: false,
    selected: [] as TendbsingleModel[],
  });

  const isCN = computed(() => locale.value === 'zh-cn');
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));
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
  ]);

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 250 : 280;
    }
    return 60;
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
      width: 280,
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
          {t('访问入口')}
        </RenderHeadCopy>
      ),
      render: ({ data }: ColumnData) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="mysql_view"
                resource={data.id}
                permission={data.permission.mysql_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.masterDomainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
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
                } />
                <span v-db-console="mysql.singleClusterList.modifyEntryConfiguration">
                  <EditEntryConfig
                    id={data.id}
                    getDetailInfo={getTendbsingleDetail}
                    permission={data.permission.access_entry_edit}
                    resource={DBTypes.MYSQL}
                    onSuccess={fetchData} />
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
      render: ({ data }: ColumnData) => (
        <TextOverflowLayout>
          {{
            default: () => data.cluster_name,
            append: () => (
              <>
                {
                  data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
                }
                {
                  data.isOffline && !data.isStarting && (
                    <db-icon
                      svg
                      type="yijinyong"
                      class="cluster-tag"
                      style="width: 38px; height: 16px;" />
                  )
                }
                {
                  isRecentDays(data.create_at, 24 * 3) && (
                    <span
                      class="glob-new-tag cluster-tag ml-4"
                      data-text="NEW" />
                  )
                }
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
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: ColumnData) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
    {
      label: t('状态'),
      field: 'status',
      width: 100,
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
      render: ({ data }: ColumnData) => {
        const info = data.status === 'normal' ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: ColumnData) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('实例'),
      field: 'masters',
      width: 180,
      minWidth: 180,
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
          {t('实例')}
        </RenderHeadCopy>
      ),
      render: ({ data }: ColumnData) => (
        <RenderInstances
          highlightIps={batchSearchIpInatanceList.value}
          data={data.masters}
          title={t('【inst】实例预览', { inst: data.master_domain })}
          role="orphan"
          clusterId={data.id}
          dataSource={getTendbsingleInstanceList}
        />
      ),
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
      render: ({ data }: ColumnData) => <span>{data.db_module_name || '--'}</span>,
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 120,
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 250,
      sort: true,
      render: ({ data }: ColumnData) => <span>{data.createAtDisplay || '--'}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
      render: ({ cell }: ColumnData) => <span>{cell || '--'}</span>,
    },
    {
      label: t('操作'),
      field: '',
      showOverflowTooltip: false,
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: ColumnData) => (
        <>
          <bk-button
            v-db-console="mysql.singleClusterList.authorize"
            text
            theme="primary"
            class="mr-8"
            onClick={() => handleShowAuthorize([data])}>
            { t('授权') }
          </bk-button>
          <auth-button
            v-db-console="mysql.haClusterList.webconsole"
            action-id="mysql_webconsole"
            resource={data.id}
            disabled={data.operationDisabled}
            permission={data.permission.mysql_webconsole}
            text
            theme="primary"
            class="mr-8"
            onClick={() => handleGoWebconsole(data.id)}>
            Webconsole
          </auth-button>
          <auth-button
            v-db-console="mysql.singleClusterList.exportData"
            action-id="mysql_dump_data"
            permission={data.permission.mysql_dump_data}
            resource={data.id}
            disabled={data.isOffline}
            text
            theme="primary"
            class="mr-16"
            onClick={() => handleShowDataExportSlider(data)}>
            { t('导出数据') }
          </auth-button>
          <MoreActionExtend v-db-console="mysql.singleClusterList.moreOperation">
            {{
              default: () => <>
                {data.isOnline ? (
                  <bk-dropdown-item v-db-console="mysql.singleClusterList.disable">
                    <OperationBtnStatusTips data={data}>
                      <auth-button
                        text
                        class="mr-8"
                        action-id="mysql_enable_disable"
                        permission={data.permission.mysql_enable_disable}
                        disabled={data.operationDisabled}
                        resource={data.id}
                        onClick={() => handleSwitchCluster(TicketTypes.MYSQL_SINGLE_DISABLE, data)}>
                        { t('禁用') }
                      </auth-button>
                    </OperationBtnStatusTips>
                  </bk-dropdown-item>
                ) : (
                  <>
                    <bk-dropdown-item v-db-console="mysql.singleClusterList.enable">
                      <OperationBtnStatusTips data={data}>
                        <auth-button
                          text
                          class="mr-8"
                          action-id="mysql_enable_disable"
                          permission={data.permission.mysql_enable_disable}
                          disabled={data.isStarting}
                          resource={data.id}
                          onClick={() => handleSwitchCluster(TicketTypes.MYSQL_SINGLE_ENABLE, data)}>
                          { t('启用') }
                        </auth-button>
                      </OperationBtnStatusTips>
                    </bk-dropdown-item>
                    <bk-dropdown-item v-db-console="mysql.singleClusterList.delete">
                      <OperationBtnStatusTips data={data}>
                        <auth-button
                          text
                          class="mr-8"
                          action-id="mysql_destroy"
                          permission={data.permission.mysql_destroy}
                          disabled={Boolean(data.operationTicketId)}
                          resource={data.id}
                          onClick={() => handleDeleteCluster(data)}>
                          { t('删除') }
                        </auth-button>
                      </OperationBtnStatusTips>
                    </bk-dropdown-item>
                  </>
                )}
              </>
            }}
          </MoreActionExtend>
        </>
      ),
    },
  ]);

  // 设置用户个人表头信息
  const disabledFields = ['master_domain'];
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label as string,
      field: item.field as string,
      disabled: disabledFields.includes(item.field as string),
    })),
    checked: [
      'master_domain',
      'status',
      'cluster_stats',
      'masters',
      'db_module_id',
      'major_version',
      'region',
    ],
    showLineHeight: false,
    trigger: 'manual' as const,
  };
  const {
    settings,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.TENDBSINGLE_TABLE_SETTINGS, defaultSettings);

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
      })
        .then(res => res.results.map(item => ({
          id: item.username,
          name: item.username,
        })));
    }

    // 不需要远层加载
    return searchSelectData.value.find(set => set.id === item.id)?.children || [];
  };

  const fetchData = () => {
    const params = getSearchSelectorParams(searchValue.value);
    tableRef.value!.fetchData(params, { ...sortValue });
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
  const getInstanceListByRole = (dataList: TendbsingleModel[], field: keyof TendbsingleModel) => dataList.reduce((result, curRow) => {
    result.push(...curRow[field] as TendbsingleModel['masters']);
    return result;
  }, [] as TendbsingleModel['masters']);

  const handleCopySelected = <T,>(field: keyof T, role?: keyof TendbsingleModel) => {
    if(role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field)
      return;
    }
    handleCopy(selected.value as T[], field)
  }

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof TendbsingleModel) => {
    const allData = await tableRef.value!.getAllData<TendbsingleModel>();
    if(allData.length === 0) {
      Message({
        theme: 'primary',
        message: '暂无数据可复制',
      });
      return;
    }
    if(role) {
      handleCopy(getInstanceListByRole(allData, role) as T[], field)
      return;
    }
    handleCopy(allData as T[], field)
  }

  // 设置行样式
  const setRowClass = (row: TendbsingleModel) => {
    const classList = [row.isOffline ? 'is-offline' : ''];
    const newClass = isRecentDays(row.create_at, 24 * 3) ? 'is-new-row' : '';
    classList.push(newClass);
    if (row.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  /**
   * 申请实例
   */
  const handleApply = () => {
    router.push({
      name: 'SelfServiceApplySingle',
      query: {
        bizId: globalBizsStore.currentBizId,
        from: route.name as string,
      },
    });
  };

  const handleGoWebconsole = (clusterId: number) => {
    router.push({
      name: 'MySQLWebconsole',
      query: {
        clusterId
      }
    });
  }

  /** 集群授权 */
  const handleShowAuthorize = (selected: TendbsingleModel[] = []) => {
    authorizeState.isShow = true;
    authorizeState.selected = selected;
  };
  const handleClearSelected = () => {
    selected.value = [];
    authorizeState.selected = [];
  };
  const handleShowExcelAuthorize = () => {
    isShowExcelAuthorize.value = true;
  };

  const handleShowDataExportSlider = (data: TendbsingleModel) => {
    currentData.value = data
    showDataExportSlider.value = true;
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  /**
   * 表格选中
   */

  const handleSelection = (data: TendbsingleModel, list: TendbsingleModel[]) => {
    selected.value = list;
  };

  /**
   * 集群启停
   */
  const handleSwitchCluster = (type: TicketTypesStrings, data: TendbsingleModel) => {
    if (!type) return;

    const isOpen = type === TicketTypes.MYSQL_SINGLE_ENABLE;
    const title = isOpen ? t('确定启用该集群') : t('确定禁用该集群');
    InfoBox({
      type: 'warning',
      title,
      content: () => (
        <div style="word-break: all;">
          {
            isOpen
              ? <p>{t('集群【name】启用后将恢复访问', { name: data.cluster_name })}</p>
              : <p>{t('集群【name】被禁用后将无法访问_如需恢复访问_可以再次「启用」', { name: data.cluster_name })}</p>
          }
        </div>
      ),
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: type,
          details: {
            cluster_ids: [data.id],
          },
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
          fetchData();
        });
      },
    });
  };

  /**
   * 删除集群
   */
  const handleDeleteCluster = (data: TendbsingleModel) => {
    const { cluster_name: name } = data;
    InfoBox({
      type: 'warning',
      title: t('确定删除该集群'),
      confirmText: t('删除'),
      confirmButtonTheme: 'danger',
      content: () => (
        <div style="word-break: all; text-align: left; padding-left: 16px;">
          <p>{t('集群【name】被删除后_将进行以下操作', { name })}</p>
          <p>{t('1_删除xx集群', { name })}</p>
          <p>{t('2_删除xx实例数据_停止相关进程', { name })}</p>
          <p>3. {t('回收主机')}</p>
        </div>
      ),
      onConfirm: async () => {
        const params = {
          bk_biz_id: globalBizsStore.currentBizId,
          ticket_type: TicketTypes.MYSQL_SINGLE_DESTROY,
          details: {
            cluster_ids: [data.id],
          },
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
          fetchData();
        });
      },
    });
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .mysql-single-cluster-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .operation-box {
      display: flex;
      flex-wrap: wrap;
      margin-bottom: 16px;

      .bk-search-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;

      .bk-table {
        height: 100% !important;
      }

      .bk-table-body {
        max-height: calc(100% - 100px);
      }

      .is-shrink-table {
        .bk-table-body {
          overflow: hidden auto;
        }
      }

      .table-wrapper {
        background-color: white;

        .bk-table {
          height: 100% !important;
        }

        .bk-table-body {
          max-height: calc(100% - 100px);
        }

        .is-shrink-table {
          .bk-table-body {
            overflow: hidden auto;
          }
        }
      }

      :deep(td .cell) {
        line-height: normal !important;

        .domain {
          display: flex;
          align-items: center;
        }

        .db-icon-copy,
        .db-icon-visible1 {
          display: none;
          margin-top: 1px;
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

      :deep(th:hover) {
        .db-icon-copy {
          display: inline-block !important;
        }
      }

      :deep(td:hover) {
        .db-icon-copy,
        .db-icon-visible1 {
          display: inline-block !important;
        }
      }

      :deep(.is-offline) {
        a {
          color: @gray-color;
        }

        .cell {
          color: @disable-color;
        }
      }
    }
  }
</style>
<style lang="less">
  .cluster-name-container {
    display: flex;
    align-items: center;
    padding: 8px 0;
    overflow: hidden;

    .cluster-name {
      .bk-button {
        display: inline-block;
        width: 100%;
        overflow: hidden;

        .bk-button-text {
          display: inline-block;
          width: 100%;
          overflow: hidden;
          line-height: 15px;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }

      &__alias {
        color: @light-gray;
      }
    }

    .cluster-tags {
      display: flex;
      max-width: 150px;
      margin-left: 4px;
      align-items: center;

      .cluster-tag {
        margin: 2px 0;
        flex-shrink: 0;
      }
    }
  }
</style>
