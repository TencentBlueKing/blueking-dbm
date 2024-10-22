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
  <div class="doris-list-page">
    <div class="header-action">
      <AuthButton
        action-id="doris_apply"
        class="mb16"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </AuthButton>
      <DropdownExportExcel
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="doris" />
      <ClusterIpCopy :selected="selected" />
      <DbSearchSelect
        class="mb16"
        :data="serachData"
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
        :data-source="getDorisList"
        :pagination-extra="paginationExtra"
        releate-url-query
        :row-class="getRowClass"
        selectable
        :settings="tableSetting"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @column-sort="columnSortChange"
        @selection="handleSelection"
        @setting-change="updateTableSettings" />
    </div>
    <DbSideslider
      v-model:is-show="isShowExpandsion"
      :title="t('xx扩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterExpansion
        v-if="operationData"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <DbSideslider
      v-model:is-show="isShowShrink"
      :title="t('xx缩容【name】', { title: 'Doris', name: operationData?.cluster_name })"
      :width="960">
      <ClusterShrink
        v-if="operationData"
        :cluster-id="operationData.id"
        :data="operationData"
        @change="fetchTableData" />
    </DbSideslider>
    <BkDialog
      v-model:is-show="isShowPassword"
      :title="t('获取访问方式')">
      <RenderPassword
        v-if="operationData"
        :cluster-id="operationData.id" />
      <template #footer>
        <BkButton @click="handleHidePassword">
          {{ t('关闭') }}
        </BkButton>
      </template>
    </BkDialog>
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox, Message } from 'bkui-vue';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import {
   getDorisInstanceList,
   getDorisList
  } from '@services/source/doris';
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
    ClusterTypes,
    DBTypes,
    TicketTypes,
    UserPersonalSettings,
  } from '@common/const';

  import RenderClusterStatus from '@components/cluster-status/Index.vue';
  import DbTable from '@components/db-table/index.vue'
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterCapacityUsageRate from '@views/db-manage/common/cluster-capacity-usage-rate/Index.vue'
  import EditEntryConfig from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import ClusterIpCopy from '@views/db-manage/common/cluster-ip-copy/Index.vue';
  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderNodeInstance from '@views/db-manage/common/RenderNodeInstance.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterExpansion from '@views/db-manage/doris/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/doris/common/shrink/Index.vue';

  import {
    getMenuListSearch,
    getSearchSelectorParams
  } from '@utils';

  const clusterId = defineModel<number>('clusterId');

  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();
  const copy = useCopy();
  const { t, locale } = useI18n();
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
    searchType: ClusterTypes.DORIS,
    attrs: [
      'bk_cloud_id',
      'db_module_id',
      'major_version',
      'region',
      'time_zone',
    ],
    fetchDataFn: () => fetchTableData(),
    defaultSearchItem: {
      name: t('访问入口'),
      id: 'domain',
    }
  })

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isInit = ref(true);

  const selected = shallowRef<DorisModel[]>([]);
  const operationData = shallowRef<DorisModel>();
  const tableDataActionLoadingMap = shallowRef<Record<number, boolean>>({});

  const serachData = computed(() => [
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
      name: t('创建人'),
      id: 'creator',
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
      name: t('时区'),
      id: 'time_zone',
      multiple: true,
      children: searchAttrs.value.time_zone,
    },
  ]);

  // const tableDataList = computed(() => tableRef.value!.getData<DorisModel>());
  // const abnormalDataList = computed(() => tableDataList.value.filter(dataItem => dataItem.isAbnormal));
  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map(item => item.id));

  const paginationExtra = computed(() => {
    if (isStretchLayoutOpen.value) {
      return { small: false };
    }

    return {
      small: true,
      align: 'left',
      layout: ['total', 'limit', 'list'],
    };
  });
  const isCN = computed(() => locale.value === 'zh-cn');

  const getRowClass = (data: DorisModel) => {
    const classList = [data.isOnline ? '' : 'is-offline'];
    const newClass = data.isNew ? 'is-new-row' : '';
    classList.push(newClass);
    if (data.id === clusterId.value) {
      classList.push('is-selected-row');
    }
    return classList.filter(cls => cls).join(' ');
  };

  const tableOperationWidth = computed(() => {
    if (!isStretchLayoutOpen.value) {
      return isCN.value ? 270 : 420;
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
      field: 'domain',
      width: 300,
      minWidth: 300,
      fixed: 'left',
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={handleCopySelected}
          onHandleCopyAll={handleCopyAll}
          config={
            [
              {
                field: 'domain',
                label: t('域名')
              },
              {
                field: 'domainDisplayName',
                label: t('域名:端口')
              }
            ]
          }
        >
          {t('访问入口')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: DorisModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <auth-button
                action-id="doris_view"
                resource={data.id}
                permission={data.permission.doris_view}
                text
                theme="primary"
                onClick={() => handleToDetails(data.id)}>
                {data.domainDisplayName}
              </auth-button>
            ),
            append: () => (
              <>
                {
                  data.domain && (
                    <RenderCellCopy copyItems={
                      [
                        {
                          value: data.domain,
                          label: t('域名')
                        },
                        {
                          value: data.domainDisplayName,
                          label: t('域名:端口')
                        }
                      ]
                    }/>
                  )
                }
                <span v-db-console="doris.clusterManage.modifyEntryConfiguration">
                  <EditEntryConfig
                    id={data.id}
                    bizId={data.bk_biz_id}
                    permission={data.permission.access_entry_edit}
                    resource={DBTypes.DORIS}
                    onSuccess={fetchTableData} />
                </span>
              </>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('集群名称'),
      width: 150,
      minWidth: 150,
      fixed: 'left',
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
      render: ({ data }: { data: DorisModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <div>
                <span>
                  {data.cluster_name}
                </span >
                <div style='color: #C4C6CC;'>{data.cluster_alias || '--'}</div>
              </div>
            ),
            append: () => (
              <>
                {
                  data.operationTagTips.map(item => <RenderOperationTag class="cluster-tag ml-4" data={item}/>)
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
                <db-icon
                  v-bk-tooltips={t('复制集群名称')}
                  type="copy"
                  class="mt-2"
                  onClick={() => copy(data.cluster_name)} />
              </>
            )
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
      render: ({ data }: {data: DorisModel}) => <span>{data.bk_cloud_name ?? '--'}</span>,
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
      render: ({ data }: {data: DorisModel}) => <RenderClusterStatus data={data.status} />,
    },
    {
      label: t('容量使用率'),
      field: 'cluster_stats',
      width: 240,
      showOverflowTooltip: false,
      render: ({ data }: {data: DorisModel}) => <ClusterCapacityUsageRate clusterStats={data.cluster_stats} />
    },
    {
      label: t('版本'),
      field: 'major_version',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.major_version,
        checked: columnCheckedMap.value.major_version,
      },
    },
    {
      label: t('地域'),
      field: 'region',
      minWidth: 100,
      filter: {
        list: columnAttrs.value.region,
        checked: columnCheckedMap.value.region,
      },
      render: ({ data }: {data: DorisModel}) => <span>{data?.region || '--'}</span>,
    },
    {
      label: t('Follower节点'),
      field: 'doris_follower',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'doris_follower')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'doris_follower')}
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
          {t('Follower节点')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="doris_follower"
          title={`【${data.domain}】follower`}
          clusterId={data.id}
          originalList={data.doris_follower}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('Observer节点'),
      field: 'doris_observer',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'doris_observer')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'doris_observer')}
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
          {t('Observer节点')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="doris_observer"
          title={`【${data.domain}】observer`}
          clusterId={data.id}
          originalList={data.doris_observer}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('热节点'),
      field: 'doris_backend_hot',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'doris_backend_hot')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'doris_backend_hot')}
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
          {t('热节点')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="doris_backend_hot"
          title={t('【xx】热节点', { name: data.domain })}
          clusterId={data.id}
          originalList={data.doris_backend_hot}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('冷节点'),
      field: 'doris_backend_cold',
      minWidth: 230,
      showOverflowTooltip: false,
      renderHead: () => (
        <RenderHeadCopy
          hasSelected={hasSelected.value}
          onHandleCopySelected={(field) => handleCopySelected(field, 'doris_backend_cold')}
          onHandleCopyAll={(field) => handleCopyAll(field, 'doris_backend_cold')}
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
          {t('冷节点')}
        </RenderHeadCopy>
      ),
      render: ({ data }: { data: DorisModel }) => (
        <RenderNodeInstance
          highlightIps={batchSearchIpInatanceList.value}
          role="doris_backend_cold"
          title={t('【xx】冷节点', { name: data.domain })}
          clusterId={data.id}
          originalList={data.doris_backend_cold}
          dataSource={getDorisInstanceList} />
      ),
    },
    {
      label: t('创建人'),
      field: 'creator',
      width: 140,
      render: ({ data }: {data: DorisModel}) => <span>{data.creator || '--'}</span>,
    },
    {
      label: t('部署时间'),
      field: 'create_at',
      width: 160,
      sort: true,
      render: ({ data }: {data: DorisModel}) => <span>{data.createAtDisplay}</span>,
    },
    {
      label: t('时区'),
      field: 'cluster_time_zone',
      width: 100,
      filter: {
        list: columnAttrs.value.time_zone,
        checked: columnCheckedMap.value.time_zone,
      },
    },
    {
      label: t('操作'),
      width: tableOperationWidth.value,
      fixed: isStretchLayoutOpen.value ? false : 'right',
      render: ({ data }: { data: DorisModel }) => {
        if (data.isOnline) {
          return [
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                theme="primary"
                action-id="doris_scale_up"
                permission={data.permission.doris_scale_up}
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowExpandsion(data)}>
                { t('扩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <OperationBtnStatusTips data={data}>
              <auth-button
                text
                theme="primary"
                class="ml-16"
                action-id="doris_shrink"
                permission={data.permission.doris_shrink}
                resource={data.id}
                disabled={data.operationDisabled}
                onClick={() => handleShowShrink(data)}>
                { t('缩容') }
              </auth-button>
            </OperationBtnStatusTips>,
            <auth-button
              text
              theme="primary"
              action-id="doris_access_entry_view"
              permission={data.permission.doris_access_entry_view}
              resource={data.id}
              class="ml-16"
              onClick={() => handleShowPassword(data)}>
              {t('获取访问方式')}
            </auth-button>,
            <bk-dropdown>
              {{
                default: () => (
                  <bk-button
                    text
                    class="ml-16">
                    <db-icon type="more" />
                  </bk-button>
                ),
                content: () => (
                  <>
                    <bk-dropdown-item>
                      <a
                        href={data.access_url}
                        target="_blank">
                        {t('管理')}
                      </a>,
                    </bk-dropdown-item>
                    <bk-dropdown-item>
                      <OperationBtnStatusTips data={data}>
                        <auth-button
                          text
                          theme="primary"
                          action-id="doris_enable_disable"
                          permission={data.permission.doris_enable_disable}
                          resource={data.id}
                          disabled={data.operationDisabled}
                          loading={tableDataActionLoadingMap.value[data.id]}
                          onClick={() => handlDisabled(data)}>
                          { t('禁用') }
                        </auth-button>
                      </OperationBtnStatusTips>
                    </bk-dropdown-item>
                  </>
                )
              }}
            </bk-dropdown>
          ];
        }
        return [
          <auth-button
            text
            theme="primary"
            action-id="doris_enable_disable"
            permission={data.permission.doris_enable_disable}
            resource={data.id}
            class="mr-16"
            loading={tableDataActionLoadingMap.value[data.id]}
            onClick={() => handleEnable(data)}>
            { t('启用') }
          </auth-button>,
          <auth-button
            text
            theme="primary"
            action-id="doris_destroy"
            permission={data.permission.doris_destroy}
            resource={data.id}
            loading={tableDataActionLoadingMap.value[data.id]}
            onClick={() => handleRemove(data)}>
            { t('删除') }
          </auth-button>,
        ];
      },
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: item.field === 'domain',
    })),
    checked: [
      'domain',
      'cluster_name',
      'bk_cloud_id',
      'major_version',
      'region',
      'status',
      'doris_follower',
      'doris_observer',
      'doris_backend_hot',
      'doris_backend_cold',
      'cluster_time_zone',
    ],
    trigger: 'manual' as const,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.DORIS_TABLE_SETTINGS, defaultSettings);

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'creator' && keyword) {
      return getMenuListSearch(item, keyword, serachData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map(value => value.id);
      return serachData.value.filter(item => !selected.includes(item.id));
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
    return serachData.value.find(set => set.id === item.id)?.children || [];
  };

  const fetchTableData = (loading?:boolean) => {
    tableRef.value!.fetchData({ ...getSearchSelectorParams }, { ...sortValue }, loading);
    isInit.value = false;
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
  const getInstanceListByRole = (dataList: DorisModel[], field: keyof DorisModel) => dataList.reduce((result, curRow) => {
    result.push(...curRow[field] as DorisModel['doris_follower']);
    return result;
  }, [] as DorisModel['doris_follower']);

  const handleCopySelected = <T,>(field: keyof T, role?: keyof DorisModel) => {
    if(role) {
      handleCopy(getInstanceListByRole(selected.value, role) as T[], field)
      return;
    }
    handleCopy(selected.value as T[], field)
  }

  const handleCopyAll = async <T,>(field: keyof T, role?: keyof DorisModel) => {
    const allData = await tableRef.value!.getAllData<DorisModel>();
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

  const handleSelection = (key: number[], list: Record<number, DorisModel>[]) => {
    selected.value = list as unknown as DorisModel[];
  };

  // 申请实例
  const handleGoApply = () => {
    router.push({
      name: 'DorisApply',
      query: {
        bizId: currentBizId,
        from: route.name as string,
      },
    });
  };

  /**
   * 查看详情
   */
  const handleToDetails = (id: number) => {
    stretchLayoutSplitScreen();
    clusterId.value = id;
  };

  // 扩容
  const handleShowExpandsion = (data: DorisModel) => {
    isShowExpandsion.value = true;
    operationData.value = data;
  };

  // 缩容
  const handleShowShrink = (data: DorisModel) => {
    isShowShrink.value = true;
    operationData.value = data;
  };

  // 禁用
  const handlDisabled =  (clusterData: DorisModel) => {
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div>
          {t('集群')} :
          <span
            style="color: #313238"
            class="ml-8">
            {clusterData.cluster_name}
          </span>
        </div>
        <div class='mt-4'>{t('被禁用后将无法访问，如需恢复访问，可以再次「启用」')}</div>
      </div>
    )
    InfoBox({
      title: t('确认禁用该集群？'),
      subTitle,
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('禁用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.DORIS_DISABLE,
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleEnable =  (clusterData: DorisModel) => {
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div>
          {t('集群')} :
          <span
            style="color: #313238"
            class="ml-8">
            {clusterData.cluster_name}
          </span>
        </div>
        <div class='mt-4'>{t('启用后，将会恢复访问')}</div>
      </div>
    )
    InfoBox({
      title: t('确认启用该集群？'),
      subTitle,
      confirmText: t('启用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.DORIS_ENABLE,
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleRemove =  (clusterData: DorisModel) => {
    const subTitle = (
      <div style="background-color: #F5F7FA; padding: 8px 16px;">
        <div>
          {t('集群')} :
          <span
            style="color: #313238"
            class="ml-8">
            {clusterData.cluster_name}
          </span>
        </div>
        <div class='mt-4'>{t('删除后将产生以下影响')}：</div>
        <div class='mt-4'>1. {t('删除xxx集群', [clusterData.cluster_name])}</div>
        <div class='mt-4'>2. {t('删除xxx实例数据，停止相关进程', [clusterData.cluster_name])}</div>
        <div class='mt-4'>3. {t('回收主机')}：</div>
      </div>
    )
    InfoBox({
      title: t('确认删除【name】集群', { name: clusterData.cluster_name }),
      subTitle,
      infoType: 'warning',
      theme: 'danger',
      confirmText: t('删除'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'left',
      footerAlign: 'center',
      onConfirm: () => {
        tableDataActionLoadingMap.value = {
          ...tableDataActionLoadingMap.value,
          [clusterData.id]: true,
        };
        createTicket({
          bk_biz_id: currentBizId,
          ticket_type: TicketTypes.DORIS_DESTROY,
          details: {
            cluster_id: clusterData.id,
          },
        })
          .then((data) => {
            tableDataActionLoadingMap.value = {
              ...tableDataActionLoadingMap.value,
              [clusterData.id]: false,
            };
            fetchTableData();
            ticketMessage(data.id);
          })
        ;
      },
    });
  };

  const handleShowPassword = (clusterData: DorisModel) => {
    operationData.value = clusterData;
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  onMounted(() => {
    if (!clusterId.value && route.query.id) {
      handleToDetails(Number(route.query.id));
    }
  });
</script>

<style lang="less">
  .doris-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      flex-wrap: wrap;

      .bk-search-select {
        flex: 1;
        max-width: 320px;
        min-width: 320px;
        margin-left: auto;
      }
    }

    .table-wrapper {
      background-color: white;

      .db-table,
      .audit-render-list,
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
      .bk-table-body {
        overflow: hidden auto;
      }
    }

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

    .is-offline {
      * {
        color: #c4c6cc !important;
      }

      a,
      i,
      .bk-button.bk-button-primary .bk-button-text {
        color: #3a84ff !important;
      }
    }

    .db-icon-copy,
    .db-icon-visible1 {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }

    tr:hover {
      .db-icon-copy,
      .db-icon-visible1 {
        display: inline-block !important;
      }
    }
  }
</style>

<style lang="less" scoped>
  .doris-list-page {
    :deep(.cell) {
      line-height: normal !important;

      .db-icon-edit {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(tr:hover) {
      .db-icon-edit {
        display: inline-block !important;
      }
    }
  }
</style>
